"""DETERMINISTIC SIGN RESOLUTION (build order Step 8) + coverage report.

Bilingual, vocabulary-aware redesign. Resolution order per item:

  Layer 1  exact bilingual match (word_en OR official ZHO word_ar)
  Layer 2  safe morphology (conservative English suffix forms only)
  Layer 3  curated aliases (data/zho/aliases.json, human-reviewed, empty
           by default - see that file's _readme)
  Layer 4  candidate retrieval: normalized token overlap against the
           whole catalog (lib/vocab_retrieval.py) - candidates only
  Layer 5  Falcon context-constrained selection: Falcon sees the source
           span, educational sentence, item, and the Layer-4 candidates
           (with their official bilingual labels + stable ids) and must
           either pick one candidate_id or answer NONE. It is never shown
           the full catalog and can never invent an id.
  Layer 6  deterministic verification: the selected id must be a real
           catalog row that was actually IN the candidate set handed to
           Falcon. Anything else is rejected outright, no matter what
           Falcon said.
  Layer 7  fallback - Arabic fingerspelling (lib/terminology.py +
           lib/fingerspell.py), same as before this redesign.

Layers 1-4 and 6 are pure deterministic Python - no model involved, and
verifiable by re-running this file with no network/model access at all.
Only Layer 5 calls Falcon, and only to CHOOSE among candidates that
deterministic retrieval already produced - it cannot fabricate a catalog
entry, per the brief's "Falcon must not become the sign authority" rule.
"""
import json
import os
import re

from lib.fingerspell import fingerspell
from lib.terminology import resolve_terminology
from lib.vocab_retrieval import (
    get_index, get_esl_zayed_index, MATCH_CANDIDATE_SELECTED, MATCH_MORPHOLOGY_CANDIDATE, MODIFIER_WORDS_EN,
)

# ESL Zayed supplementary WORD-level candidate source (smallest-safe
# integration per data/zho/spike_mediapipe/ab_experiment_20260823/FINAL_REPORT.md
# §Z/§AF). Only consulted AFTER ZHO's own deterministic layers (exact,
# morphology, alias, ZHO candidate-selection) have already failed to
# produce a verified sign for the SAME item - see _esl_zayed_resolution()'s
# call site in resolve_item(). ZHO always retains priority: an ESL Zayed
# candidate can never override an existing EXACT_EN/EXACT_AR/ALIAS/
# candidate-selected ZHO match, because this function is only ever reached
# when lex["row"] is already None. Defaults ON so the production website
# path actually exercises it (per the task's hard requirement); can be
# disabled for a run via MOI_DISABLE_ESL_ZAYED=1 (e.g. for exact A/B
# comparisons against the pre-integration baseline).
MATCH_ESL_ZAYED_EXACT = "ESL_ZAYED_EXACT"
MATCH_ESL_ZAYED_CANDIDATE_SELECTED = "ESL_ZAYED_CANDIDATE_SELECTED"

ESL_ZAYED_SELECTION_SYSTEM_PROMPT = """You are helping select a SUPPLEMENTARY sign-language vocabulary entry for one
word/phrase in a school lesson video, drawn from an OBSERVED Emirati educational video source (NOT the institutional
UAE sign reference - this is a secondary, supplementary source, used only because no institutional sign was found).
You will be given the educational sentence, the exact source span it came from, the specific semantic item that needs
a sign, and a short list of CANDIDATE supplementary entries (each with a stable id and its English/Arabic labels).

Choose the candidate whose meaning is genuinely equivalent to the semantic item IN THIS CONTEXT - not merely a word
that looks similar. If none of the candidates are a legitimate match, you MUST answer NONE. Do not force a match. A
wrong sign is worse than no sign.

You may ONLY select an id that appears in the candidate list below, or answer NONE. Never invent an id.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"selected_candidate_id": "<id from the list, or null>", "reason": "<one short sentence>", "confidence": "high|medium|low"}
"""


def _call_falcon_esl_zayed_selection(item_text: str, source_span: str, educational_sentence: str,
                                      candidates: list, model: str) -> dict:
    from lib.episode_builder import _call_ollama_raw
    from lib.understand import UnderstandError

    candidate_payload = [
        {"id": c["supplementary_id"], "word_en": c.get("english_meaning"), "word_ar": c.get("arabic_text")}
        for c in candidates
    ]
    prompt_input = {
        "source_span": source_span,
        "educational_sentence": educational_sentence,
        "semantic_item": item_text,
        "candidates": candidate_payload,
    }
    prompt = (f"{ESL_ZAYED_SELECTION_SYSTEM_PROMPT}\n\nINPUT:\n"
              f"{json.dumps(prompt_input, ensure_ascii=False)}\n\nJSON:")
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {"selected_candidate_id": None, "reason": f"model call failed: {e}", "confidence": "low"}

    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"selected_candidate_id": None, "reason": "model output was not valid JSON", "confidence": "low"}
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return {"selected_candidate_id": None, "reason": "model output was not valid JSON", "confidence": "low"}

    sel = parsed.get("selected_candidate_id")
    if sel in ("NONE", "None", "none", ""):
        sel = None
    return {
        "selected_candidate_id": sel,
        "reason": parsed.get("reason", ""),
        "confidence": parsed.get("confidence", "low"),
    }


def _esl_zayed_row_is_renderable(row: dict) -> bool:
    """Deterministic authorization gate (brief §4). A row may only ever be
    used if ALL of: word-level content_type, complete source provenance
    (video id + segment boundaries), and non-empty English/Arabic labels.
    Mirrors the discipline of the ZHO `has_video` check in
    _deterministic_lexical_resolution() above."""
    if not row:
        return False
    if row.get("content_type") != "WORD":
        return False
    if not row.get("youtube_video_id"):
        return False
    if row.get("segment_start_s") is None or row.get("segment_end_s") is None:
        return False
    if not row.get("english_meaning") or not row.get("arabic_text"):
        return False
    return True


def _esl_zayed_resolution(item_text: str, model: str, source_span: str,
                           educational_sentence: str, allow_candidate_selection: bool) -> dict:
    """ESL Zayed fallback layer. Only ever called once ZHO's own
    deterministic resolution has already returned no row for this item -
    see resolve_item(). Returns the same shaped dict as
    _deterministic_lexical_resolution() (row/method/information_loss/
    match_reason/candidates/falcon_selection) so callers can treat it
    uniformly, but every non-null row carries source=ESL_ZAYED /
    source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE so it is never
    mistaken for an institutional ZHO match downstream."""
    idx = get_esl_zayed_index()
    if not idx.rows:
        return {"row": None, "method": None, "candidates": [], "match_reason": "ESL Zayed supplementary catalog is empty or missing"}

    exact = idx.exact_match(item_text)
    if exact and _esl_zayed_row_is_renderable(exact):
        return {"row": exact, "method": MATCH_ESL_ZAYED_EXACT, "information_loss": LOSS_FULL,
                "match_reason": (f"ESL Zayed exact WORD-level match: query='{item_text}' == supplementary "
                                  f"english_meaning/arabic_text='{exact.get('english_meaning')}' / '{exact.get('arabic_text')}' "
                                  f"(source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)")}

    candidates = idx.retrieve_candidates(item_text, top_n=5)
    if not candidates:
        return {"row": None, "method": None, "candidates": [], "match_reason": "no ESL Zayed lexical candidates found"}

    if not allow_candidate_selection:
        return {"row": None, "method": None, "candidates": candidates,
                "match_reason": f"{len(candidates)} ESL Zayed candidates found but Falcon selection unavailable/disabled"}

    selection = _call_falcon_esl_zayed_selection(item_text, source_span, educational_sentence, candidates, model)
    selected_id = selection.get("selected_candidate_id")
    candidate_ids = {c["supplementary_id"] for c in candidates}

    if selected_id and selected_id in candidate_ids:
        verified_row = idx.by_id.get(selected_id)
        if verified_row and _esl_zayed_row_is_renderable(verified_row):
            loss = classify_information_loss(item_text, verified_row.get("english_meaning"))
            if loss in (LOSS_ESSENTIAL_INFORMATION_LOSS, LOSS_AMBIGUOUS):
                return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                        "information_loss": loss,
                        "match_reason": (f"Falcon selected ESL Zayed candidate '{verified_row.get('english_meaning')}' "
                                          f"(id={selected_id}) but it was rejected by the information-loss safeguard "
                                          f"({loss}) - a false lexical sign is worse than honest fingerspelling")}
            if _looks_arabic(verified_row.get("english_meaning") or "") or not _looks_arabic(verified_row.get("arabic_text") or ""):
                # Arabic-script integrity guard (brief §D/§9): the ESL Zayed
                # arabic_text field must actually contain Arabic script, and
                # the english_meaning field must not itself be mixed/garbled
                # Arabic - reject rather than trust a corrupted catalog row.
                return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                        "match_reason": (f"ESL Zayed candidate id={selected_id} failed the Arabic-script integrity "
                                          f"check (arabic_text/english_meaning fields malformed) - rejected")}
            return {
                "row": verified_row, "method": MATCH_ESL_ZAYED_CANDIDATE_SELECTED, "candidates": candidates,
                "falcon_selection": selection, "information_loss": loss,
                "match_reason": (f"Falcon selected ESL Zayed candidate '{verified_row.get('english_meaning')}' "
                                  f"from {len(candidates)} retrieved candidates (id={selected_id}); "
                                  f"reason: {selection.get('reason', '')}; verified id is in candidate set, "
                                  f"content_type=WORD, source segment/video metadata complete, "
                                  f"information_loss={loss}; source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE"),
            }
        return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                "match_reason": f"Falcon selected ESL Zayed id={selected_id} but it failed deterministic authorization (not WORD-level, or incomplete provenance) - rejected"}

    if selected_id and selected_id not in candidate_ids:
        return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                "match_reason": f"Falcon selected ESL Zayed id={selected_id} which was NOT in the candidate set - rejected outright (possible hallucination)"}

    return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
            "match_reason": f"Falcon reviewed {len(candidates)} ESL Zayed candidates and answered NONE: {selection.get('reason', '')}"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")

STATUS_VERIFIED = "VERIFIED_SIGN"
STATUS_FINGERSPELL = "FINGERSPELL_CANDIDATE"
STATUS_UNSUPPORTED = "UNSUPPORTED"
STATUS_REVIEW = "REVIEW_REQUIRED"

# Information-loss classification (brief §J). Applied to every candidate
# (morphology-candidate or Falcon-selected) BEFORE it is allowed to count
# as a verified sign. Exact/alias matches are always FULL (the catalog
# entry IS the query, or a human curated the equivalence).
LOSS_FULL = "FULL"
LOSS_CORE_WITH_MODIFIER_LOSS = "CORE_WITH_MODIFIER_LOSS"
LOSS_ESSENTIAL_INFORMATION_LOSS = "ESSENTIAL_INFORMATION_LOSS"
LOSS_AMBIGUOUS = "AMBIGUOUS"

_WORD_RE = re.compile(r"[A-Za-z']+")


def classify_information_loss(item_text: str, selected_word_en: str) -> str:
    """General multi-token semantic-preservation safeguard (brief §I/§J).

    Splits the query into MODIFIER tokens (quantity/intensity/negation,
    see MODIFIER_WORDS_EN) and CONTENT tokens (everything else - the
    presumed semantic head(s)). A candidate is only FULL/acceptable if it
    represents a content token (or the whole query, when there are no
    modifiers). A candidate that represents only a modifier while a
    content/head token exists - e.g. "ONE BROTHER" -> "One" - drops the
    semantic head and is ESSENTIAL_INFORMATION_LOSS, which the caller
    must reject rather than count as a verified match. A candidate that
    represents the head but drops a modifier - e.g. "VERY HOT" -> "Hot" -
    keeps the core meaning and is CORE_WITH_MODIFIER_LOSS (acceptable,
    but flagged distinctly from FULL so headline coverage metrics stay
    conservative)."""
    tokens = [t.lower() for t in _WORD_RE.findall(item_text or "")]
    if not tokens:
        return LOSS_AMBIGUOUS
    content = [t for t in tokens if t not in MODIFIER_WORDS_EN]
    modifiers = [t for t in tokens if t in MODIFIER_WORDS_EN]
    sel = (selected_word_en or "").strip().lower()
    sel_tokens = set(_WORD_RE.findall(sel))

    if not modifiers:
        return LOSS_FULL

    if not content:
        # query is entirely modifiers (rare) - nothing to lose besides
        # the modifier itself, treat as full representation of itself
        return LOSS_FULL

    if any(c in sel_tokens or c == sel for c in content):
        return LOSS_CORE_WITH_MODIFIER_LOSS

    if any(m in sel_tokens or m == sel for m in modifiers):
        return LOSS_ESSENTIAL_INFORMATION_LOSS

    return LOSS_AMBIGUOUS

_ARABIC_CHAR_RE = re.compile(r"[؀-ۿ]")


def _looks_arabic(text: str) -> bool:
    """True if text contains any Arabic-script character. Deliberately
    permissive (mixed Arabic+numerals/punctuation still counts) - this is
    only used to catch the opposite failure mode: an item with NO Arabic
    script at all inside an Arabic-source lesson."""
    return bool(text) and bool(_ARABIC_CHAR_RE.search(text))

CANDIDATE_SELECTION_SYSTEM_PROMPT = """You are helping select a sign-language dictionary entry for one word/phrase
in a school lesson video. You will be given the educational sentence, the exact source span it came from, the
specific semantic item that needs a sign, and a short list of CANDIDATE dictionary entries (each with a stable id
and its official English and Arabic labels).

Choose the candidate whose meaning is genuinely equivalent to the semantic item IN THIS CONTEXT - not merely a
word that looks similar. If none of the candidates are a legitimate match, you MUST answer NONE. Do not force a
match. A wrong sign is worse than no sign.

You may ONLY select an id that appears in the candidate list below, or answer NONE. Never invent an id.

Respond with ONLY a JSON object, no other text, no markdown fences:
{"selected_candidate_id": "<id from the list, or null>", "reason": "<one short sentence>", "confidence": "high|medium|low"}
"""


def _load_catalog_index() -> dict:
    """Kept for backward compatibility with any external callers that
    used this function name directly; delegates to the shared VocabIndex
    so there is exactly one place that loads/normalizes catalog.json."""
    idx = get_index()
    return idx.en_exact


def _match_verified_sign(term_en: str):
    """Backward-compatible: exact EN-only match. New code should use
    the layered resolution in resolve_item() instead."""
    matches = get_index().en_exact.get(term_en.strip().lower())
    return matches[0] if matches else None


def _call_falcon_candidate_selection(item_text: str, source_span: str,
                                      educational_sentence: str,
                                      candidates: list, model: str) -> dict:
    from lib.episode_builder import _call_ollama_raw
    from lib.understand import UnderstandError

    candidate_payload = [
        {"id": c["id"], "word_en": c.get("word_en"), "word_ar": c.get("word_ar"), "category": c.get("category")}
        for c in candidates
    ]
    prompt_input = {
        "source_span": source_span,
        "educational_sentence": educational_sentence,
        "semantic_item": item_text,
        "candidates": candidate_payload,
    }
    prompt = (f"{CANDIDATE_SELECTION_SYSTEM_PROMPT}\n\nINPUT:\n"
              f"{json.dumps(prompt_input, ensure_ascii=False)}\n\nJSON:")
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {"selected_candidate_id": None, "reason": f"model call failed: {e}", "confidence": "low"}

    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"selected_candidate_id": None, "reason": "model output was not valid JSON", "confidence": "low"}
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return {"selected_candidate_id": None, "reason": "model output was not valid JSON", "confidence": "low"}

    sel = parsed.get("selected_candidate_id")
    if sel in ("NONE", "None", "none", ""):
        sel = None
    return {
        "selected_candidate_id": sel,
        "reason": parsed.get("reason", ""),
        "confidence": parsed.get("confidence", "low"),
    }


def _deterministic_lexical_resolution(item_text: str, model: str, source_span: str,
                                       educational_sentence: str, allow_candidate_selection: bool) -> dict:
    """Runs Layers 1-6. Returns a dict with match/None and diagnostic
    trail (query, normalized forms tried, candidates considered) so
    every non-fingerspell resolution is fully auditable per the brief's
    traceability requirements."""
    idx = get_index()

    row, method = idx.exact_match(item_text)
    if row:
        return {"row": row, "method": method, "information_loss": LOSS_FULL,
                "match_reason": f"exact bilingual match: query='{item_text}' == catalog word_en/word_ar='{row.get('word_en')}' / '{row.get('word_ar')}'"}

    row, method, tok, form = idx.morphology_match(item_text)
    morphology_candidate = None
    if row and method == "MORPHOLOGY_EN":
        loss = classify_information_loss(item_text, row.get("word_en"))
        if loss != LOSS_ESSENTIAL_INFORMATION_LOSS:
            return {"row": row, "method": method, "information_loss": loss,
                    "match_reason": f"safe morphology match: '{tok}' -> normalized form '{form}' == catalog word_en='{row.get('word_en')}'"}
        # safe (plural) morphology still lost the semantic head in a
        # multi-token item - don't auto-verify, fall through to candidate
        # retrieval/Falcon like any other unresolved item.
    elif row and method == MATCH_MORPHOLOGY_CANDIDATE:
        # RISKY (-ed/-ing) morphology: morphological relatedness alone
        # does not establish contextual semantic equivalence (brief §H).
        # Treat as ONE candidate that must clear the same Falcon
        # contextual-selection + information-loss gate as lexical
        # candidates below, never auto-verified.
        morphology_candidate = dict(row)
        morphology_candidate["_morphology_source_token"] = tok
        morphology_candidate["_morphology_source_form"] = form

    row, method = idx.alias_match(item_text)
    if row:
        return {"row": row, "method": method, "information_loss": LOSS_FULL,
                "match_reason": f"curated alias match: query='{item_text}' -> catalog word_en='{row.get('word_en')}' (data/zho/aliases.json)"}

    candidates = idx.retrieve_candidates(item_text, top_n=5)
    candidate_ids_seen = {c["id"] for c in candidates}
    if morphology_candidate is not None and morphology_candidate["id"] not in candidate_ids_seen:
        candidate_ids_seen.add(morphology_candidate["id"])
        candidates.append(morphology_candidate)

    # Optional Layer 4b (off by default): local multilingual embedding
    # retrieval, benchmarked against plain lexical/token-overlap in
    # scripts/vocab_embedding_benchmark.py (MiniLM: Recall@1=0.73,
    # Recall@5=0.93 on a 30-pair bilingual synonym benchmark, vs 0.07/0.10
    # for lexical alone) — materially better recall, so it's wired in
    # here, but still gated behind MOI_VOCAB_EMBEDDING_MODEL since it adds
    # a torch/sentence-transformers dependency most runs don't need.
    # Candidates from either source go through the SAME Falcon selection
    # + deterministic verification below - embedding similarity never
    # authorizes a sign by itself.
    embedding_model_key = os.environ.get("MOI_VOCAB_EMBEDDING_MODEL")
    if embedding_model_key:
        try:
            from lib.vocab_embedding_st import get_index as get_embedding_index
            emb_idx = get_embedding_index(embedding_model_key)
            for c in emb_idx.retrieve_candidates(item_text, top_n=5):
                if c["id"] not in candidate_ids_seen and c.get("similarity", 0) >= 0.55:
                    candidate_ids_seen.add(c["id"])
                    candidates.append(c)
        except Exception:
            pass  # optional path - never blocks resolution if the extra isn't installed

    if not candidates:
        return {"row": None, "method": None, "candidates": [], "match_reason": "no lexical (or embedding, if enabled) candidates found"}

    if not allow_candidate_selection:
        return {"row": None, "method": None, "candidates": candidates,
                "match_reason": f"{len(candidates)} lexical candidates found but Falcon selection unavailable/disabled"}

    selection = _call_falcon_candidate_selection(item_text, source_span, educational_sentence, candidates, model)
    selected_id = selection.get("selected_candidate_id")

    # Layer 6 - deterministic verification: selected id must be one of
    # the candidates actually handed to Falcon, and must exist in the
    # catalog with a video. Anything else is rejected regardless of what
    # Falcon said - Falcon never gets to unilaterally decide a sign.
    candidate_ids = {c["id"] for c in candidates}
    if selected_id and selected_id in candidate_ids:
        verified_row = idx.by_id.get(selected_id)
        if verified_row and verified_row.get("has_video"):
            loss = classify_information_loss(item_text, verified_row.get("word_en"))
            is_morphology_candidate = morphology_candidate is not None and selected_id == morphology_candidate["id"]
            match_method = MATCH_MORPHOLOGY_CANDIDATE if is_morphology_candidate else MATCH_CANDIDATE_SELECTED
            if loss in (LOSS_ESSENTIAL_INFORMATION_LOSS, LOSS_AMBIGUOUS):
                return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                        "information_loss": loss,
                        "match_reason": (f"Falcon selected candidate '{verified_row.get('word_en')}' (id={selected_id}) "
                                          f"but it was rejected by the information-loss safeguard ({loss}): the query "
                                          f"'{item_text}' has a semantic head/content token this candidate does not "
                                          f"represent - a false lexical sign is worse than honest fingerspelling")}
            source_desc = ("risky morphology form (-ed/-ing reduction) confirmed by Falcon in context"
                            if is_morphology_candidate else
                            f"Falcon selected candidate '{verified_row.get('word_en')}' from {len(candidates)} retrieved candidates")
            return {
                "row": verified_row, "method": match_method, "candidates": candidates,
                "falcon_selection": selection, "information_loss": loss,
                "match_reason": (f"{source_desc} (id={selected_id}); reason: {selection.get('reason', '')}; "
                                  f"verified id is in candidate set, has video, information_loss={loss}"),
            }
        return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                "match_reason": f"Falcon selected id={selected_id} but it failed deterministic verification (missing catalog row or video) - rejected"}

    if selected_id and selected_id not in candidate_ids:
        return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
                "match_reason": f"Falcon selected id={selected_id} which was NOT in the candidate set - rejected outright (possible hallucination)"}

    return {"row": None, "method": None, "candidates": candidates, "falcon_selection": selection,
            "match_reason": f"Falcon reviewed {len(candidates)} candidates and answered NONE: {selection.get('reason', '')}"}


def resolve_item(item_text: str, source_language: str, source_span: str,
                  educational_sentence: str, model: str, allow_candidate_selection: bool = True) -> dict:
    """Resolves one semantic_sign_plan item end-to-end through the
    layered bilingual vocabulary-aware resolution, falling back to
    Arabic fingerspelling only when no verified lexical sign is found."""
    lex = _deterministic_lexical_resolution(item_text, model, source_span, educational_sentence, allow_candidate_selection)
    if lex["row"]:
        supporting = []
        if os.environ.get("MOI_DISABLE_ESL_ZAYED") != "1":
            esl_evidence = get_esl_zayed_index().exact_match(item_text)
            if esl_evidence:
                # ZHO was selected; any ESL Zayed evidence for the same item
                # is recorded as a SUPPORTING source, never as the render
                # source - per brief §6 ("never say the rendered asset came
                # from both").
                supporting.append({
                    "source": "ESL_ZAYED", "source_authority": "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE",
                    "supplementary_id": esl_evidence.get("supplementary_id"),
                })
        return {
            "term": item_text,
            "status": STATUS_VERIFIED,
            "catalog_ref": lex["row"],
            "match_method": lex["method"],
            "fallback_type": None,
            "information_loss": lex.get("information_loss", LOSS_FULL),
            "match_reason": lex["match_reason"],
            "retrieval_trace": {k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
            "review_required": False,
            "render_source": "ZHO",
            "source_authority": "INSTITUTIONAL_UAE_REFERENCE",
            "supporting_sources": supporting,
        }

    # 1c. ZHO has no verified sign for this item - fall back to the ESL
    # Zayed supplementary WORD catalog (smallest-safe integration, see
    # _esl_zayed_resolution() above). This can NEVER run before ZHO has
    # already had its full chance above (exact/morphology/alias/ZHO
    # candidate-selection all failed to find lex["row"]), so ZHO priority
    # is structurally guaranteed, not just a policy statement.
    if os.environ.get("MOI_DISABLE_ESL_ZAYED") != "1":
        esl = _esl_zayed_resolution(item_text, model, source_span, educational_sentence, allow_candidate_selection)
        if esl.get("row"):
            esl_row = esl["row"]
            return {
                "term": item_text,
                "status": STATUS_VERIFIED,
                "catalog_ref": None,
                "supplementary_ref": esl_row,
                "match_method": esl["method"],
                "fallback_type": None,
                "information_loss": esl.get("information_loss", LOSS_FULL),
                "match_reason": esl["match_reason"],
                "retrieval_trace": {**{k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
                                     "esl_zayed_trace": {k: v for k, v in esl.items() if k not in ("row", "method", "match_reason")}},
                "review_required": False,
                "render_source": "ESL_ZAYED",
                "source_authority": "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE",
                "supporting_sources": [],
            }

    # 1b. Guard against a real observed Falcon failure mode: for an
    # Arabic-source lesson, the semantic-plan step (lib/sign_plan.py)
    # occasionally drifts into English or Arabizi/transliteration
    # ("AB", "ASA3A", "SA'IDAH") instead of Arabic script, even though the
    # rest of the plan is correctly Arabic. Sending that straight into
    # fingerspell() would silently burn a fingerspell attempt on text
    # that can never resolve against the Arabic alphabet map (every
    # "letter" fails) - flag it plainly instead, per source-grounding
    # requirements (don't silently mistranslate/normalize the wrong way).
    source_is_arabic = source_language == "ar" or _looks_arabic(source_span)
    if source_is_arabic and item_text.strip() and not _looks_arabic(item_text):
        return {
            "term": item_text,
            "status": STATUS_REVIEW,
            "catalog_ref": None,
            "match_method": None,
            "fallback_type": None,
            "retrieval_trace": {k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
            "match_reason": (f"semantic_sign_plan item '{item_text}' is not Arabic script despite an Arabic-source "
                              f"lesson (likely model drift to English/transliteration) - flagged rather than "
                              f"fingerspelled, since it cannot resolve against the Arabic alphabet map"),
            "review_required": True,
            "render_source": "FINGERSPELL",
            "source_authority": "NONE",
            "gap_reason": "NO_SUPPORTED_LEXICAL_SIGN",
            "supporting_sources": [],
        }

    # 2. No lexical match -> attempt Arabic fingerspelling fallback.
    term_info = resolve_terminology(item_text, source_language, source_span, educational_sentence, model)
    if term_info["translation_status"] not in ("OK", "NOT_NEEDED") or not term_info["arabic_term"]:
        return {
            "term": item_text,
            "status": STATUS_REVIEW,
            "catalog_ref": None,
            "match_method": None,
            "fallback_type": None,
            "terminology": term_info,
            "retrieval_trace": {k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
            "match_reason": "no verified lexical sign, and Arabic terminology translation was not usable",
            "review_required": True,
            "render_source": "FINGERSPELL",
            "source_authority": "NONE",
            "gap_reason": "NO_SUPPORTED_LEXICAL_SIGN",
            "supporting_sources": [],
        }

    # 2b. The Arabic academic term Falcon produced may itself BE an
    # official ZHO word_ar (per brief §16 - prefer an authoritative
    # Arabic sign label over spelling the term out letter by letter).
    # This match is inherently less trustworthy than a direct item-text
    # match (it depends on Falcon's translation being exactly right), so
    # it is flagged review_required and given its own match_method
    # rather than silently treated as an ordinary EXACT_AR hit.
    idx = get_index()
    ar_row, ar_method = idx.exact_match(term_info["arabic_term"])
    if ar_row and ar_row.get("has_video"):
        return {
            "term": item_text,
            "status": STATUS_VERIFIED,
            "catalog_ref": ar_row,
            "match_method": "EXACT_AR_VIA_TERMINOLOGY",
            "fallback_type": None,
            "terminology": term_info,
            "retrieval_trace": {k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
            "match_reason": (f"no direct lexical match for '{item_text}', but Falcon's Arabic terminology "
                              f"'{term_info['arabic_term']}' exactly matches official ZHO word_ar for "
                              f"'{ar_row.get('word_en')}' — used instead of fingerspelling per official-label preference"),
            "review_required": True,
            "render_source": "ZHO",
            "source_authority": "INSTITUTIONAL_UAE_REFERENCE",
            "supporting_sources": [],
        }

    spelled = fingerspell(term_info["arabic_term"])
    if spelled["fully_resolved"]:
        return {
            "term": item_text,
            "status": STATUS_FINGERSPELL,
            "catalog_ref": None,
            "match_method": None,
            "fallback_type": "FINGERSPELL",
            "terminology": term_info,
            "fingerspell": spelled,
            "retrieval_trace": {k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
            "match_reason": f"no verified lexical sign for '{item_text}' ({lex['match_reason']}); fingerspelled Arabic term '{term_info['arabic_term']}' — all letters resolved against data/zho/arabic_alphabet_map.json",
            "review_required": False,
            "render_source": "FINGERSPELL",
            "source_authority": "NONE",
            "gap_reason": "NO_SUPPORTED_LEXICAL_SIGN",
            "supporting_sources": [],
        }

    return {
        "term": item_text,
        "status": STATUS_UNSUPPORTED,
        "catalog_ref": None,
        "match_method": None,
        "fallback_type": "FINGERSPELL",
        "terminology": term_info,
        "fingerspell": spelled,
        "retrieval_trace": {k: v for k, v in lex.items() if k not in ("row", "method", "match_reason")},
        "match_reason": f"no verified lexical sign, and fingerspelling '{term_info['arabic_term']}' left unresolved letters {spelled['unresolved_letters']}",
        "review_required": True,
        "render_source": "FINGERSPELL",
        "source_authority": "NONE",
        "gap_reason": "NO_SUPPORTED_LEXICAL_SIGN",
        "supporting_sources": [],
    }


def resolve_unit(unit: dict, source_language: str, model: str, allow_candidate_selection: bool = True) -> dict:
    resolutions = [
        resolve_item(item, source_language, unit["source_span"], unit.get("educational_sentence", ""), model,
                     allow_candidate_selection=allow_candidate_selection)
        for item in unit.get("semantic_sign_plan", [])
    ]
    unit_review_required = unit.get("review_required", False) or any(r["review_required"] for r in resolutions)
    return {**unit, "sign_resolution": resolutions, "review_required": unit_review_required}


def resolve_units(units: list, source_language: str, model: str, allow_candidate_selection: bool = True) -> list:
    return [resolve_unit(u, source_language, model, allow_candidate_selection=allow_candidate_selection) for u in units]


def coverage_report(units: list) -> dict:
    """Coverage numbers kept SEPARATE per Step 9 - never conflated.
    Adds a breakdown by match_method so bilingual/morphology/alias/
    candidate-selected recoveries are visible distinctly from plain
    exact matches, per the brief's traceability requirement."""
    all_resolutions = [r for u in units for r in u.get("sign_resolution", [])]
    total = len(all_resolutions)
    verified = sum(1 for r in all_resolutions if r["status"] == STATUS_VERIFIED)
    verified_full = sum(1 for r in all_resolutions
                         if r["status"] == STATUS_VERIFIED and r.get("information_loss", LOSS_FULL) == LOSS_FULL)
    verified_partial = sum(1 for r in all_resolutions
                            if r["status"] == STATUS_VERIFIED
                            and r.get("information_loss") == LOSS_CORE_WITH_MODIFIER_LOSS)
    fingerspell_ok = sum(1 for r in all_resolutions if r["status"] == STATUS_FINGERSPELL)
    unsupported = sum(1 for r in all_resolutions if r["status"] == STATUS_UNSUPPORTED)
    review = sum(1 for r in all_resolutions if r["status"] == STATUS_REVIEW)

    # ESL Zayed vs ZHO kept STRUCTURALLY separate everywhere (brief §7) -
    # never folded into the "verified lexical coverage" headline, which
    # historically means ZHO/institutional coverage only.
    verified_zho = sum(1 for r in all_resolutions
                        if r["status"] == STATUS_VERIFIED and r.get("render_source") == "ZHO")
    verified_esl_zayed = sum(1 for r in all_resolutions
                              if r["status"] == STATUS_VERIFIED and r.get("render_source") == "ESL_ZAYED")
    zho_coverage_pct = round(100.0 * verified_zho / total, 1) if total else 0.0
    esl_zayed_supplementary_coverage_pct = round(100.0 * verified_esl_zayed / total, 1) if total else 0.0
    combined_known_source_lexical_coverage_pct = round(100.0 * (verified_zho + verified_esl_zayed) / total, 1) if total else 0.0

    # Headline coverage stays conservative: FULL representations only.
    # CORE_WITH_MODIFIER_LOSS matches are real, verified, renderable signs
    # (a false lexical sign is worse than fingerspelling, but a modifier-
    # loss match is not false - it is a legitimate, partial, representation)
    # - they are reported SEPARATELY, never folded into the headline number.
    full_pct = round(100.0 * verified_full / total, 1) if total else 0.0
    lexical_pct = round(100.0 * verified / total, 1) if total else 0.0
    partial_pct = round(100.0 * verified_partial / total, 1) if total else 0.0
    renderable_pct = round(100.0 * (verified + fingerspell_ok) / total, 1) if total else 0.0

    by_method = {}
    for r in all_resolutions:
        if r["status"] == STATUS_VERIFIED:
            by_method[r["match_method"]] = by_method.get(r["match_method"], 0) + 1

    return {
        "total_sign_units": total,
        "verified_signs": verified,
        "verified_signs_full": verified_full,
        "verified_signs_partial_modifier_loss": verified_partial,
        "verified_by_match_method": by_method,
        "fallback_candidates": fingerspell_ok,
        "unsupported_units": unsupported,
        "review_required_units": review,
        "full_verified_lexical_coverage_pct": full_pct,
        "verified_lexical_sign_coverage_pct": lexical_pct,
        "partial_lexical_representation_pct": partial_pct,
        "renderable_coverage_with_fallback_pct": renderable_pct,
        "verified_signs_zho": verified_zho,
        "verified_signs_esl_zayed_supplementary": verified_esl_zayed,
        "institutional_zho_coverage_pct": zho_coverage_pct,
        "supplementary_observed_emirati_coverage_pct": esl_zayed_supplementary_coverage_pct,
        "combined_known_source_lexical_coverage_pct": combined_known_source_lexical_coverage_pct,
        "_note": (
            "full_verified_lexical_coverage_pct is the conservative headline number - only "
            "information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected "
            "candidate confirmed to represent the query's full semantic content). "
            "verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS "
            "matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); "
            "partial_lexical_representation_pct isolates just that subset so it is never silently "
            "folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. "
            "'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED "
            "before verification and never appear here - they fall through to fingerspelling/review. "
            "renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, "
            "NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a "
            "verified lexical sign — see fallback_type on each resolution. verified_by_match_method "
            "distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED "
            "and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically "
            "retrieved candidates and passed deterministic verification (including the information-loss "
            "gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR "
            "matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY "
            "render_source=ZHO matches (the institutional UAE sign reference). "
            "supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an "
            "observed, supplementary, NOT institutionally verified source - verification_status is always "
            "SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct "
            "is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / "
            "verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never "
            "folded into ZHO's own headline coverage number."
        ),
    }
