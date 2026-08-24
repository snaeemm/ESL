"""VOCABULARY-AWARE RETRIEVAL (bilingual ZHO resolution redesign).

Implements the controlled, local, deterministic-first retrieval layers used
by lib/sign_resolver.py before falling back to fingerspelling:

  Layer 1 - bilingual deterministic exact match (word_en / word_ar)
  Layer 2 - safe morphology (conservative English suffix stripping;
            conservative Arabic diacritic/alef normalization)
  Layer 3 - curated aliases (data/zho/aliases.json) - system-derived,
            never overwrites official word_en/word_ar
  Layer 4 - candidate retrieval for STILL-unresolved items: normalized
            token overlap against the whole catalog (word_en + word_ar).
            This produces candidates only - it is NOT a match. Nothing
            from this layer is used as a sign without Falcon selection
            (sign_resolver.py) plus deterministic verification.

No embeddings/vector search: with ~1,143 entries, token overlap is enough
signal for Falcon to choose from, and it keeps the whole thing dependency-
free and instantly inspectable (see coverage_report.md's own reasoning for
rejecting fuzzy/substring matching in favor of explicit, auditable rules).

Root-cause finding this module responds to (Cells episode, 27 items):
almost none of the fingerspelled concepts existed in the catalog even as
single, morphologically-reduced words (`small`, `part`, `animal`, `have`,
`body` etc. are all absent) - so Layers 1-3 mostly help GENERAL-vocabulary
lessons, not domain-mismatched ones like Cells. Layer 4 candidates plus
Falcon's contextual judgement (in sign_resolver.py) are what can recover a
few more legitimate matches beyond that; true science vocabulary gaps stay
gaps and should fall through to fingerspelling, not get force-matched.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")
ALIASES_PATH = os.path.join(ROOT, "data", "zho", "aliases.json")

MATCH_EXACT_EN = "EXACT_EN"
MATCH_EXACT_AR = "EXACT_AR"
MATCH_MORPHOLOGY_EN = "MORPHOLOGY_EN"
MATCH_MORPHOLOGY_AR = "MORPHOLOGY_AR"
MATCH_ALIAS = "ALIAS"
MATCH_CLITIC_AR = "CLITIC_AR"
MATCH_CANDIDATE_SELECTED = "CANDIDATE_SELECTED"
MATCH_MORPHOLOGY_CANDIDATE = "MORPHOLOGY_CANDIDATE"

# Quantifiers/intensifiers/negation that can appear alongside a semantic
# head noun in a multi-word item (e.g. "ONE BROTHER", "VERY HOT"). Used by
# sign_resolver.py's information-loss check: a candidate selection must not
# silently pick one of these MODIFIER words while dropping the head.
MODIFIER_WORDS_EN = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "some", "many", "few", "several", "no", "all", "every", "each", "both",
    "very", "so", "quite", "extremely", "really", "too",
    "not", "never", "no",
}

_STOPWORDS_EN = {
    "a", "an", "the", "of", "is", "are", "was", "were", "be", "to", "and",
    "or", "in", "on", "at", "for", "with", "very", "every", "all", "many",
}

_ARABIC_DIACRITICS = re.compile(r"[ؗ-ًؚ-ْٰۖ-ۭ]")
_TATWEEL = "ـ"


def _normalize_ar(text: str) -> str:
    """Conservative Arabic normalization only: strip diacritics/tatweel
    and unify the three alef-with-hamza/madda forms to bare alef (a
    standard, meaning-preserving spelling normalization - NOT a stemmer).
    Ta marbuta, ya/alef maqsura, and all consonants are left untouched
    because collapsing those CAN change meaning (brief's explicit
    instruction not to build an aggressive Arabic stemmer)."""
    if not text:
        return ""
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.replace(_TATWEEL, "")
    text = re.sub(r"[إأآ]", "ا", text)
    return text.strip().lower()


def _english_suffix_forms(word: str) -> tuple:
    """Conservative, deterministic English morphology, split into two
    trust tiers:

      SAFE forms (plural/singular only) - number rarely changes a word's
      core meaning ("cats" -> "cat"), so these auto-verify at Layer 2.

      RISKY forms (-ing/-ed reduction to a bare verb) - these change
      grammatical role, and a past-participle/adjectival use is often a
      false friend for the base verb's sign meaning (e.g. "CALLED" in
      "called cells" means NAMED, not the verb "to call"/summon). These
      are returned separately so the caller can route them through
      Falcon contextual confirmation (MORPHOLOGY_CANDIDATE) instead of
      auto-verifying - per brief: morphological relatedness does not by
      itself establish contextual semantic equivalence.

    Returns (safe_forms, risky_forms); every candidate form is only ever
    ACCEPTED if it exactly equals a real catalog word_en - this function
    just proposes forms, it never itself decides a match."""
    w = word.lower()
    safe = {w}
    risky = set()
    if w.endswith("ies") and len(w) > 4:
        safe.add(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3:
        safe.add(w[:-2])
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        safe.add(w[:-1])
    if w.endswith("ing") and len(w) > 5:
        risky.add(w[:-3])
        risky.add(w[:-3] + "e")
    if w.endswith("ed") and len(w) > 4:
        risky.add(w[:-2])
        risky.add(w[:-1])
    return safe, risky


def _tokenize_en(text: str) -> list:
    return [t for t in re.findall(r"[A-Za-z']+", text.lower()) if t not in _STOPWORDS_EN]


def _tokenize_ar(text: str) -> list:
    return [t for t in re.findall(r"[؀-ۿ]+", _normalize_ar(text))]


# Clitics that may be conservatively stripped from the QUERY side only
# (definite article + single-letter conjunctions/prepositions). Never
# applied to catalog word_ar values, which are already bare lexical
# forms. Order matters: try the two-letter combos (conjunction/prep +
# "ال") before the bare single-letter clitic, so "والشمس" strips to
# "شمس" in one step rather than stopping at "الشمس".
_AR_CLITIC_PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")


def _strip_ar_clitics(word: str) -> list:
    """Returns candidate stripped forms of a normalized Arabic word, most
    aggressive first, WITHOUT deciding whether any of them is valid. Not
    a stemmer: only ever removes a single leading clitic. Caller must
    verify each candidate actually resolves against the catalog before
    using it (see VocabIndex.clitic_match) — this function only proposes."""
    candidates = []
    for prefix in _AR_CLITIC_PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= 2:
            candidates.append(word[len(prefix):])
    return candidates


class VocabIndex:
    """Loads catalog.json + aliases.json once and exposes deterministic
    lookup + candidate-retrieval methods. Cheap to build (~1,143 rows);
    the module-level singleton below avoids rebuilding it per item."""

    def __init__(self, catalog_path: str = CATALOG_PATH, aliases_path: str = ALIASES_PATH):
        with open(catalog_path, encoding="utf-8") as f:
            self.rows = json.load(f)
        self.by_id = {r["id"]: r for r in self.rows}

        self.en_exact = {}
        self.ar_exact = {}
        self.en_tokens_by_row = {}
        self.ar_tokens_by_row = {}
        for r in self.rows:
            if r.get("word_en"):
                self.en_exact.setdefault(r["word_en"].strip().lower(), []).append(r)
                self.en_tokens_by_row[r["id"]] = set(_tokenize_en(r["word_en"]))
            if r.get("word_ar"):
                self.ar_exact.setdefault(_normalize_ar(r["word_ar"]), []).append(r)
                self.ar_tokens_by_row[r["id"]] = set(_tokenize_ar(r["word_ar"]))

        self.aliases = {}
        if os.path.exists(aliases_path):
            with open(aliases_path, encoding="utf-8") as f:
                raw_aliases = json.load(f)
            for entry in raw_aliases.get("aliases", []):
                catalog_id = entry.get("catalog_id")
                if catalog_id not in self.by_id:
                    continue
                for a in entry.get("aliases_en", []):
                    self.aliases.setdefault(a.strip().lower(), []).append(("en", catalog_id))
                for a in entry.get("aliases_ar", []):
                    self.aliases.setdefault(_normalize_ar(a), []).append(("ar", catalog_id))

    # -- Layer 1: exact bilingual match --------------------------------
    def exact_match(self, term: str):
        key_en = term.strip().lower()
        if key_en in self.en_exact:
            return self.en_exact[key_en][0], MATCH_EXACT_EN
        key_ar = _normalize_ar(term)
        if key_ar and key_ar in self.ar_exact:
            return self.ar_exact[key_ar][0], MATCH_EXACT_AR
        return None, None

    # -- Layer 2: safe morphology ---------------------------------------
    def morphology_match(self, term: str):
        """Returns (row, method, tok, form). SAFE (plural) forms return
        MATCH_MORPHOLOGY_EN and auto-verify. RISKY (-ed/-ing) forms return
        MATCH_MORPHOLOGY_CANDIDATE - the caller must NOT treat this as a
        verified sign; it needs Falcon contextual confirmation same as a
        Layer-4 candidate (see sign_resolver.py)."""
        for tok in _tokenize_en(term) or [term.strip().lower()]:
            safe, risky = _english_suffix_forms(tok)
            for form in safe:
                if form != tok and form in self.en_exact:
                    return self.en_exact[form][0], MATCH_MORPHOLOGY_EN, tok, form
            for form in risky:
                if form in self.en_exact:
                    return self.en_exact[form][0], MATCH_MORPHOLOGY_CANDIDATE, tok, form
        # whole-phrase reduction: single-word items only, multi-word
        # phrases are not stemmed as a unit (would risk false collapses)
        words = term.strip().split()
        if len(words) == 1:
            safe, risky = _english_suffix_forms(words[0])
            for form in safe:
                if form in self.en_exact:
                    return self.en_exact[form][0], MATCH_MORPHOLOGY_EN, words[0], form
            for form in risky:
                if form in self.en_exact:
                    return self.en_exact[form][0], MATCH_MORPHOLOGY_CANDIDATE, words[0], form
        return None, None, None, None

    # -- Layer 3: curated aliases ----------------------------------------
    def alias_match(self, term: str):
        key_en = term.strip().lower()
        if key_en in self.aliases:
            lang, catalog_id = self.aliases[key_en][0]
            return self.by_id[catalog_id], MATCH_ALIAS
        key_ar = _normalize_ar(term)
        if key_ar and key_ar in self.aliases:
            lang, catalog_id = self.aliases[key_ar][0]
            return self.by_id[catalog_id], MATCH_ALIAS
        return None, None

    # -- Layer 2b: conservative Arabic clitic stripping (verify-before-use) --
    def clitic_match(self, term: str):
        """Strips at most one leading clitic (definite article and/or a
        single conjunction/preposition letter) from the QUERY term only,
        and returns a match ONLY if the resulting stripped form is an
        actual exact hit against catalog word_ar (never touches
        catalog values, never a blind substitution - see
        _strip_ar_clitics's docstring). Returns (row, method,
        original_term, stripped_form) or (None, None, None, None)."""
        normalized = _normalize_ar(term)
        if not normalized:
            return None, None, None, None
        for stripped in _strip_ar_clitics(normalized):
            if stripped in self.ar_exact:
                return self.ar_exact[stripped][0], MATCH_CLITIC_AR, term, stripped
        return None, None, None, None

    # -- Layer 4: candidate retrieval (NOT a match) -----------------------
    def retrieve_candidates(self, term: str, top_n: int = 5) -> list:
        """Normalized token overlap against word_en and word_ar across the
        whole catalog. Returns up to top_n rows with score > 0, most
        overlap first, ties broken by catalog order (deterministic).
        These are candidates for Falcon to judge in context - never used
        directly as a resolved sign."""
        q_en = set(_tokenize_en(term))
        q_ar = set(_tokenize_ar(term))
        if not q_en and not q_ar:
            return []
        scored = []
        for r in self.rows:
            score = 0
            if q_en:
                score += len(q_en & self.en_tokens_by_row.get(r["id"], set()))
            if q_ar:
                score += len(q_ar & self.ar_tokens_by_row.get(r["id"], set()))
            if score > 0:
                scored.append((score, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:top_n]]


_INDEX = None


def get_index() -> VocabIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = VocabIndex()
    return _INDEX


def reset_index_cache():
    """Test/dev helper - forces the next get_index() to reload from disk."""
    global _INDEX
    _INDEX = None
