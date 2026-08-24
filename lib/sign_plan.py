"""SEMANTIC SIGN PLAN stage (build order Step 6 — required change from the
key-terms-only approach).

For each episode unit, derives a small ordered list of semantic items
(concepts/actions/entities) that together communicate the unit's
educational meaning — not just its literal key_terms. This is explicitly
NOT a claim of validated Arabic Sign Language grammar or word order; it
is a semantic plan a downstream deterministic resolver can attach real
signs/fingerspelling to. Anything the model is unsure about is marked
uncertain, not silently smoothed over.
"""
import json
import re

from lib.episode_builder import _call_ollama_raw, _parse_json_array
from lib.understand import UnderstandError
from lib.vocab_retrieval import get_index, _tokenize_en, _tokenize_ar

_ARABIC_CHAR_RE = re.compile(r"[؀-ۿ]")


def _looks_arabic(text: str) -> bool:
    return bool(text) and bool(_ARABIC_CHAR_RE.search(text))


# Reinforces the base prompt's "SAME language as the input sentence" rule
# for Arabic input specifically. Observed Falcon drift (brief §M): for
# Arabic-source sentences, occasional items come back in Latin-script
# English or Arabizi transliteration ("AB", "ASA3A", "SA'IDAH") instead of
# Arabic script. This is a targeted prompt reinforcement only - the
# deterministic Arabic-script guard in lib/sign_resolver.py
# (`_looks_arabic`) stays in place regardless of whether this helps, since
# a prompt instruction is never itself a guarantee.
_ARABIC_REINFORCEMENT = ("\n\nThe input sentence above is written in Arabic. Every item you output MUST be "
                          "written in Arabic script (not Latin letters, not Arabizi/transliteration like "
                          "\"3\" for \"ع\"). If you cannot express an item in Arabic script, omit it rather "
                          "than transliterating.")

SIGN_PLAN_SYSTEM_PROMPT = """You are helping plan a sign-language video for a school lesson.
You will be given one educational sentence, its concept name, its key_terms, all grounded in a
verified academic source, and RELEVANT_INVENTORY — real sign-language dictionary entries that are
contextually related to this sentence's topic, each labeled with its source: ZHO entries are the
institutional UAE sign reference (preferred); ESL_ZAYED entries are an observed Emirati educational
source, supplementary and NOT independently verified (usable, but only when nothing suitable exists
in ZHO, and never in place of a ZHO entry that already fits).

Break the sentence's MEANING down into a short ordered list of semantic items — the core
entities/actions/relationships that must be communicated, not just a list of nouns. Prefer verbs and
relationships over dropping them. Each item is a short word or phrase in the SAME language as the
input sentence.

Your goal is to express the SAME grounded lesson meaning as faithfully as possible while making good
use of RELEVANT_INVENTORY - this is realization within the source's meaning, not rewriting the lesson
to whatever is easiest to sign. RELEVANT_INVENTORY is NOT a menu you must use, and it is NOT the full
dictionary — it is only a bounded, relevant sample. Concretely:
- Prefer simpler, source-faithful wording that matches an inventory entry WHEN it communicates the
  same educational meaning as the sentence, equally well, without changing or dumbing down the
  scientific/factual content.
- If a single concept in the sentence can be safely expressed as two or more inventory entries WITHOUT
  changing its meaning (e.g. a compound idea splitting into its component real-world parts), prefer
  that decomposition over a single fingerspelled item - but only when every part is still implied by
  the sentence itself, never invented.
- Do NOT drop or distort a required technical term just because it has no inventory entry available —
  keep it as its own item; a downstream step will fingerspell technical terms that have no dictionary
  sign. Never replace a specific required fact (e.g. a named technical term the sentence depends on)
  with an unrelated, vaguely-related, or merely-easier inventory entry just because that entry exists.
- ZHO entries are preferred over ESL_ZAYED entries when both would communicate the same meaning
  equally well - do not pick an ESL_ZAYED entry merely because it happens to appear earlier in the
  list.

Example (English input "The membrane controls what enters and leaves the cell."):
["MEMBRANE", "CONTROL/REGULATE", "ENTER", "LEAVE", "CELL"]

Rules:
- 3 to 7 items per sentence. Do not pad or invent content not implied by the sentence.
- Do not include grammatical function words (the, a, of, that) as separate items. More generally:
  each item must name an independent, meaning-bearing educational concept (a thing, action, quality,
  or relationship someone could picture, define, or point to on its own) - never a spoken-language
  connective, particle, or grammatical marker whose only job is to glue other words together
  syntactically. Apply this test to EVERY item regardless of language or part of speech: "if I removed
  every other item, would this item alone still refer to a concept a viewer could picture and that the
  lesson is actually about?" If the answer is no - it only exists to link, mark case/direction, negate,
  or grammatically connect neighboring words - leave it out; its grammatical role will be implied by
  the ordering and choice of the surrounding items, not stated as its own item. This applies equally to
  English words (the, a, of, that, to, and) and to their equivalents and function-word/clitic
  counterparts in any other language you are outputting in (definite articles, conjunctions,
  prepositions, direction/case particles, etc.) - the test is about the WORD'S ROLE in the sentence, not
  a fixed list of words to avoid.
- Do not confuse a short word with a function word: a short verb, quality, or concrete noun (e.g. "GO",
  "HOT", "SUN") is still meaning-bearing and must be kept if the sentence depends on it.
- If you are not confident a faithful semantic breakdown is possible for this sentence, output
  an empty array [] instead of guessing.

Output ONLY a JSON array of strings. No other text, no markdown code fences.
"""


def _vocabulary_hints(sentence: str, key_terms: list, top_n: int = 15) -> list:
    """Cheap, deterministic, local: token-overlap retrieval against the
    bilingual catalog (lib/vocab_retrieval.py) to surface a handful of
    contextually-related real dictionary entries as hints for the
    planner. Does NOT decide anything by itself and is not authoritative
    - the resolver (lib/sign_resolver.py) still does deterministic
    matching + verification independently downstream. Cached per-call is
    fine: the catalog index itself is process-cached in vocab_retrieval."""
    idx = get_index()
    query = sentence + " " + " ".join(key_terms or [])
    is_arabic = _looks_arabic(sentence)
    q_tokens = set(_tokenize_ar(query)) if is_arabic else set(_tokenize_en(query))
    if not q_tokens:
        return []
    scored = []
    for r in idx.rows:
        tokens_by_row = idx.ar_tokens_by_row if is_arabic else idx.en_tokens_by_row
        overlap = len(q_tokens & tokens_by_row.get(r["id"], set()))
        if overlap > 0:
            scored.append((overlap, r))
    scored.sort(key=lambda x: -x[0])
    return [f"{r['word_en']} ({r['word_ar']})" if r.get("word_ar") else r["word_en"] for _, r in scored[:top_n]]


def _relevant_inventory(sentence: str, key_terms: list, top_n: int = 12) -> list:
    """Final-pass upgrade (Part B, "inventory-aware realization"): the
    SAME bounded, deterministic token-overlap retrieval as
    _vocabulary_hints() above, but also including safe WORD-level ESL
    Zayed supplementary candidates - not just ZHO - and returning each
    candidate SOURCE-LABELED (source=ZHO/authority=INSTITUTIONAL or
    source=ESL_ZAYED/authority=SUPPLEMENTARY_UNVERIFIED) so the planner
    is explicitly aware which vocabulary is institutional vs observed/
    unverified, per the product requirement that Falcon "know enough
    about vocabulary we can ACTUALLY render" - not just a few incidental
    hint strings, and not the whole catalog dumped into context (bounded
    top_n, same discovery-only retrieval as the resolver's own
    idx.retrieve_candidates - no embeddings, nothing re-enabled that was
    rejected). This does NOT authorize any sign - lib/sign_resolver.py
    still independently, deterministically re-verifies every item
    regardless of what this list contains."""
    idx = get_index()
    query = sentence + " " + " ".join(key_terms or [])
    is_arabic = _looks_arabic(sentence)
    q_tokens = set(_tokenize_ar(query)) if is_arabic else set(_tokenize_en(query))
    if not q_tokens:
        return []

    scored = []
    for r in idx.rows:
        tokens_by_row = idx.ar_tokens_by_row if is_arabic else idx.en_tokens_by_row
        overlap = len(q_tokens & tokens_by_row.get(r["id"], set()))
        if overlap > 0:
            scored.append((overlap, "ZHO", "INSTITUTIONAL_UAE_REFERENCE", r.get("word_en"), r.get("word_ar")))
    try:
        from lib.vocab_retrieval import get_esl_zayed_index
        esl_idx = get_esl_zayed_index()
        for r in esl_idx.rows:
            if r.get("content_type") != "WORD":
                continue  # only the safe WORD-level subset, per the brief
            en_toks = set(_tokenize_en(r.get("english_meaning") or ""))
            ar_toks = set(_tokenize_ar(r.get("arabic_text") or ""))
            overlap = len(q_tokens & (ar_toks if is_arabic else en_toks))
            if overlap > 0:
                scored.append((overlap, "ESL_ZAYED", "SUPPLEMENTARY_UNVERIFIED",
                                r.get("english_meaning"), r.get("arabic_text")))
    except Exception:
        pass  # ESL Zayed inventory is a supplement - never blocks planning if unavailable

    scored.sort(key=lambda x: -x[0])
    out = []
    for _, source, authority, word_en, word_ar in scored[:top_n]:
        label = f"{word_en} ({word_ar})" if word_ar else word_en
        out.append({"label": label, "source": source, "authority": authority})
    return out


def _check_semantic_preservation(unit: dict, items: list) -> tuple:
    """Semantic-preservation gate (Part B, mandatory per product
    requirement - catches regressions like SCHOOL STARTS->SCHOOL and
    guards against a plan silently dropping a source-grounded concept).

    Deterministic, no extra model call: every one of the unit's own
    ALREADY-GROUNDED key_terms (produced upstream by UNDERSTAND, which is
    source-span-verified - this function trusts that grounding, it does
    not re-derive it) must be represented by at least one token in at
    least one plan item, in the SAME language/script as that key_term.
    A key_term with zero token overlap against every plan item is
    evidence the plan silently dropped it - not proof (a paraphrase could
    legitimately use a different word), so this is conservative: it flags
    for review rather than hard-blocking, and never deletes/rewrites the
    plan itself, mirroring the existing single-item-collapse guard below.
    Returns (preserved: bool, missing_key_terms: list)."""
    key_terms = unit.get("key_terms") or []
    if not key_terms or not items:
        return True, []
    item_tokens = set()
    for it in items:
        item_tokens |= set(_tokenize_ar(it)) | set(_tokenize_en(it))
    missing = []
    for kt in key_terms:
        kt_tokens = set(_tokenize_ar(kt)) | set(_tokenize_en(kt))
        if kt_tokens and not (kt_tokens & item_tokens):
            missing.append(kt)
    return (len(missing) == 0), missing


def build_sign_plan(unit: dict, model: str) -> dict:
    """Returns the unit augmented with a "semantic_sign_plan" list and a
    "semantic_plan_status" of either "OK" or "REVIEW_REQUIRED" (model
    declined / returned empty / call failed)."""
    if not unit.get("educational_sentence"):
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": "no educational_sentence available to plan from"}

    hints = _vocabulary_hints(unit["educational_sentence"], unit.get("key_terms", []))
    relevant_inventory = _relevant_inventory(unit["educational_sentence"], unit.get("key_terms", []))
    prompt_input = {
        "concept": unit["concept"],
        "key_terms": unit.get("key_terms", []),
        "educational_sentence": unit["educational_sentence"],
        "relevant_inventory": relevant_inventory,
    }
    system_prompt = SIGN_PLAN_SYSTEM_PROMPT
    if _looks_arabic(unit["educational_sentence"]):
        system_prompt += _ARABIC_REINFORCEMENT
    prompt = f"{system_prompt}\n\nINPUT:\n{json.dumps(prompt_input, ensure_ascii=False)}\n\nJSON array:"
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": f"local model call failed: {e}"}

    items = _parse_json_array(raw)
    if items is None or not isinstance(items, list):
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": "model output was not a parseable JSON array"}

    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": "model declined to produce a semantic breakdown (returned empty)",
                "vocabulary_hints_used": hints, "relevant_inventory_used": relevant_inventory}

    # Blocker B guard (information loss, e.g. "school starts" -> only
    # SCHOOL, silently dropping the predicate START): a single-item plan
    # is only trustworthy when the source sentence itself is essentially
    # single-concept. When the sentence's own content-word count (crude,
    # deterministic, language-aware token count with stopwords already
    # stripped by _tokenize_en/_tokenize_ar - not a parser, just a
    # conservative proxy for "there is more than one thing being said
    # here") suggests multiple independent concepts but the plan
    # collapsed to just one item, that is exactly the silent-collapse
    # failure mode this guard exists to catch. We do NOT have evidence
    # this is an intentional valid ASL/EmSL formulation (no linguistic
    # planning signal says so), so per the brief we must not let it pass
    # as silently "OK" - flag it for conservative fallback (review /
    # restructuring) instead of dropping meaning unnoticed. The item(s)
    # already produced are kept (never silently discarded), but
    # possible_information_loss + REVIEW_REQUIRED make sure this unit is
    # never treated as a complete, information-preserving plan downstream.
    is_arabic = _looks_arabic(unit["educational_sentence"])
    content_tokens = set(_tokenize_ar(unit["educational_sentence"])) if is_arabic \
        else set(_tokenize_en(unit["educational_sentence"]))
    possible_information_loss = len(items) == 1 and len(content_tokens) >= 2
    if possible_information_loss:
        return {**unit, "semantic_sign_plan": items, "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": (
                    f"possible information loss: sentence has {len(content_tokens)} distinct content "
                    f"words ({sorted(content_tokens)}) but the semantic plan collapsed to a single item "
                    f"{items!r} - no evidence this single-sign collapse is an intentional valid ASL/EmSL "
                    f"formulation, so it is flagged for review rather than silently treated as complete"),
                "possible_information_loss": True,
                "vocabulary_hints_used": hints, "relevant_inventory_used": relevant_inventory}

    # Mandatory semantic-preservation gate (Part B): even a multi-item
    # plan can silently drop a GROUNDED concept (key_terms come from
    # UNDERSTAND, already source-span-verified) if the inventory-aware
    # realization above substituted/omitted one while filling out the
    # rest of the list. This is a SEPARATE, complementary check to the
    # single-item-collapse guard above (that one catches a plan that's
    # too SHORT relative to sentence complexity; this one catches a
    # plan of any length that doesn't cover every already-grounded
    # key_term). Conservative: flags for review, keeps the plan, never
    # silently deletes/rewrites - if it cannot be established that a
    # realization preserved meaning, the safer path is human review, not
    # a forced accept OR a forced discard.
    preserved, missing_key_terms = _check_semantic_preservation(unit, items)
    if not preserved:
        return {**unit, "semantic_sign_plan": items, "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": (
                    f"semantic-preservation gate failed: grounded key_term(s) {missing_key_terms!r} have no "
                    f"token overlap with any item in the realized plan {items!r} - the inventory-aware "
                    f"realization may have silently dropped or substituted required source-grounded meaning, "
                    f"so this plan is flagged for review rather than silently treated as complete"),
                "possible_information_loss": True, "semantic_preservation_missing_key_terms": missing_key_terms,
                "vocabulary_hints_used": hints, "relevant_inventory_used": relevant_inventory}

    return {**unit, "semantic_sign_plan": items, "semantic_plan_status": "OK",
            "possible_information_loss": False, "vocabulary_hints_used": hints,
            "relevant_inventory_used": relevant_inventory}


def build_sign_plans(units: list, model: str) -> list:
    return [build_sign_plan(u, model) for u in units]
