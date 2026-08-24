"""SCRATCH / EXPERIMENTAL — Part 5-12: the five-case Falcon A/B experiment.

Plan A = calls real production functions (lib.understand, lib.episode_builder,
lib.sign_plan, lib.sign_resolver) UNCHANGED, read-only import. Same Ollama
model/config as production (lib.understand.DEFAULT_MODEL, temperature=0).

Plan B = a NEW scratch evidence-aware planner defined only in this file.
Does not modify any lib/ file. Reuses the SAME grounded UNDERSTAND+STRUCTURE
output as Plan A (so both plans work from an identical grounded meaning),
then re-plans the sign-oriented breakdown using explicit ZHO + ESL Zayed
evidence handed to the same local Falcon model, with a hard deterministic
rejection of any evidence id not actually supplied (Part 11 authority
boundary). Per Part 3's finding (recall@1=0.2, verdict NOT_USEFUL), ESL
Zayed PHRASE/SENTENCE examples are NOT injected as retrievable evidence
here — only WORD-level ESL Zayed lexical evidence is used, consistent with
that finding.

Does not touch MediaPipe/avatar rendering. Does not modify production.
Does not commit/push.
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, ROOT)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SPIKE_DIR = os.path.join(ROOT, "data", "zho", "spike_mediapipe")

from lib.source_loader import detect_language
from lib.understand import extract_concepts, DEFAULT_MODEL, _call_ollama, UnderstandError
from lib.episode_builder import build_episode, _call_ollama_raw
from lib.sign_plan import build_sign_plans, _looks_arabic
from lib.sign_resolver import resolve_units, coverage_report, STATUS_VERIFIED, STATUS_FINGERSPELL, STATUS_UNSUPPORTED, STATUS_REVIEW
from lib.vocab_retrieval import get_index, _tokenize_en, _tokenize_ar
from lib.terminology import resolve_terminology
from lib.fingerspell import fingerspell

MODEL = DEFAULT_MODEL  # same as production default, unchanged

# ---------------------------------------------------------------------
# The five development cases.
# ---------------------------------------------------------------------
with open(os.path.join(ROOT, "content", "test_b_family_school.md"), encoding="utf-8") as f:
    TEXT_ENGLISH_FAMILY = f.read()
with open(os.path.join(ROOT, "content", "test_c_family_school_ar.md"), encoding="utf-8") as f:
    TEXT_ARABIC_FAMILY = f.read()
with open(os.path.join(ROOT, "content", "test_d_emirati.md"), encoding="utf-8") as f:
    TEXT_EMIRATI = f.read()
with open(os.path.join(ROOT, "content", "grade6_science_ch3_cells.md"), encoding="utf-8") as f:
    _cells_full = f.read()
# Bounded excerpt (task allows bounding sample sizes) - the "What is a
# cell?" + "What is inside a cell?" sections, which carry the case's
# core specialist vocabulary (cell, organelle, membrane, nucleus,
# cytoplasm, mitochondria) plus ordinary supporting vocabulary.
TEXT_CELLS = _cells_full.split("## Plant cells")[0].split("# Grade 6")[1].strip()
TEXT_CELLS = "Cells\n\n" + TEXT_CELLS
with open(os.path.join(OUT_DIR, "photosynthesis_constructed.md"), encoding="utf-8") as f:
    TEXT_PHOTOSYNTHESIS = f.read().split("chlorophyll")[0]  # header note stripped below
TEXT_PHOTOSYNTHESIS = TEXT_PHOTOSYNTHESIS.split("\n\n", 1)[-1] if "\n\n" in TEXT_PHOTOSYNTHESIS else TEXT_PHOTOSYNTHESIS
with open(os.path.join(OUT_DIR, "photosynthesis_constructed.md"), encoding="utf-8") as f:
    _photo_raw = f.read()
TEXT_PHOTOSYNTHESIS = _photo_raw.split("\n\nPlants make")[1]
TEXT_PHOTOSYNTHESIS = "Plants make" + TEXT_PHOTOSYNTHESIS

CASES = [
    {"id": "english_family_school", "label": "English Family/School", "text": TEXT_ENGLISH_FAMILY, "lang": "en",
     "source_note": "content/test_b_family_school.md (pre-existing repo development fixture, used verbatim)"},
    {"id": "arabic_family_school", "label": "Arabic/MSA Family/School", "text": TEXT_ARABIC_FAMILY, "lang": "ar",
     "source_note": "content/test_c_family_school_ar.md (pre-existing repo development fixture, used verbatim)"},
    {"id": "emirati_dialect", "label": "Emirati/dialectal development test", "text": TEXT_EMIRATI, "lang": "ar",
     "source_note": "content/test_d_emirati.md (pre-existing repo development fixture, used verbatim)"},
    {"id": "cells", "label": "Cells", "text": TEXT_CELLS, "lang": "en",
     "source_note": "content/grade6_science_ch3_cells.md, bounded excerpt: 'What is a cell?' + 'What is inside a cell?' sections only"},
    {"id": "photosynthesis", "label": "Photosynthesis", "text": TEXT_PHOTOSYNTHESIS, "lang": "en",
     "source_note": "CONSTRUCTED for this experiment (no existing fixture found) - see photosynthesis_constructed.md"},
]

FUNCTION_WORDS_EN = {"is", "are", "was", "were", "the", "a", "an", "of", "to", "and", "or", "that", "in", "on", "at"}
FUNCTION_WORDS_AR_HINT = {"هو", "هي", "كان", "كانت", "ال", "و", "في", "على", "من", "إلى"}


# ---------------------------------------------------------------------
# PLAN A - unchanged production call path.
# ---------------------------------------------------------------------
def run_plan_a(text, lang):
    t0 = time.time()
    understand = extract_concepts(text, model=MODEL)
    episode = build_episode(understand["concepts"], model=MODEL, target_duration_s=45)
    units = build_sign_plans(episode["units"], model=MODEL)
    units = resolve_units(units, source_language=lang, model=MODEL, allow_candidate_selection=True)
    cov = coverage_report(units)
    return {"understand": understand, "episode": episode, "units": units, "coverage": cov,
            "elapsed_s": round(time.time() - t0, 1)}


# ---------------------------------------------------------------------
# PLAN B - evidence-aware scratch planner (this file only).
# ---------------------------------------------------------------------
_esl_word_rows_cache = None


def _esl_word_candidates(query_tokens_en, top_n=5):
    """Lightweight deterministic token-overlap retrieval over ESL Zayed
    WORD-type records (mirrors the same style as lib.vocab_retrieval's
    lexical layer, applied to the ESL Zayed corpus instead of ZHO) - kept
    intentionally simple/deterministic here since MiniLM lexical results
    for this corpus were already characterized in retrieval_tests.py
    (Part 2) and this experiment just needs candidates to hand to Falcon,
    not a second benchmark."""
    global _esl_word_rows_cache
    if _esl_word_rows_cache is None:
        with open(os.path.join(SPIKE_DIR, "esl_zayed_full_93video_corpus_20260823.json"), encoding="utf-8") as f:
            corpus = json.load(f)
        _esl_word_rows_cache = [r for r in corpus if r.get("content_type") == "WORD" and r.get("english_meaning_from_video")]
    scored = []
    qset = set(query_tokens_en)
    for r in _esl_word_rows_cache:
        rtoks = set(_tokenize_en(r["english_meaning_from_video"]))
        overlap = len(qset & rtoks)
        if overlap:
            scored.append((overlap, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:top_n]]


EVIDENCE_AWARE_SYSTEM_PROMPT = """You are helping plan a sign-language video for a school lesson.
You will be given one educational sentence, its concept name, key_terms, and a list of EVIDENCE
items. Each evidence item is a REAL sign that genuinely exists and can be rendered, with a
unique evidence_id, its source (ZHO = the official UAE institutional sign dictionary, or
ESL_ZAYED = an observed Emirati educational YouTube source, supplementary/not institutionally
verified), and its English/Arabic label(s).

Your job: break the sentence's MEANING down into an ordered list of semantic items (the core
entities/actions/relationships the sentence depends on), and for EACH item either:
  (a) select ONE evidence_id from the EVIDENCE list below whose real sign genuinely expresses
      that same meaning in this context, or
  (b) set evidence_id to null if no supplied evidence genuinely matches (this is CORRECT and
      EXPECTED behavior for genuine vocabulary gaps - a missing evidence_id is not a failure).

Hard rules (do not violate any of these):
1. You may ONLY output an evidence_id that appears in the EVIDENCE list below, or null. Never
   invent, guess, or reuse an id from outside this list.
2. Preserve the ESSENTIAL educational meaning of the sentence. Do not omit a required technical
   or factual concept just because it has no evidence - keep it as its own item with evidence_id
   null; it will be fingerspelled downstream. Never replace a specific required fact/technical
   term with an easier but different concept merely because the easier concept has evidence.
3. Prefer using genuine available evidence WHERE it expresses the same meaning, over leaving an
   item without evidence, but never force a wrong/approximate match - a wrong sign is worse than
   fingerspelling.
4. Do not include grammatical function words (is, are, was, the, a, of, that, and, in Arabic:
   equivalents like هو/كان/ال/و/في/من as their own item) as separate items - same rule as
   ordinary sign planning.
5. 3 to 7 items per sentence. Do not pad or invent content not implied by the sentence.
6. You never "know" a sign yourself - you may only select from the EVIDENCE list or say null.

Output ONLY a JSON array of objects, in the SAME language as the input sentence for the
"semantic_concept" field:
[{"semantic_concept": "...", "evidence_id": "<id from EVIDENCE list or null>"}, ...]
No other text, no markdown fences.
"""


def build_evidence_for_unit(unit, is_arabic):
    idx = get_index()
    query = unit["educational_sentence"] + " " + " ".join(unit.get("key_terms", []))
    zho_lexical = idx.retrieve_candidates(query, top_n=6)
    esl_candidates = []
    if not is_arabic:
        q_tokens = _tokenize_en(query)
        esl_candidates = _esl_word_candidates(q_tokens, top_n=5)
    else:
        # Arabic input: ESL Zayed candidates are matched via arabic_caption
        # token overlap - simple deterministic overlap, same spirit as
        # above, bounded to avoid a second full benchmark.
        global _esl_word_rows_cache
        if _esl_word_rows_cache is None:
            with open(os.path.join(SPIKE_DIR, "esl_zayed_full_93video_corpus_20260823.json"), encoding="utf-8") as f:
                corpus = json.load(f)
            _esl_word_rows_cache = [r for r in corpus if r.get("content_type") == "WORD" and r.get("english_meaning_from_video")]
        qset = set(_tokenize_ar(query))
        scored = []
        for r in _esl_word_rows_cache:
            rtoks = set(_tokenize_ar(r.get("arabic_caption", "")))
            overlap = len(qset & rtoks)
            if overlap:
                scored.append((overlap, r))
        scored.sort(key=lambda x: -x[0])
        esl_candidates = [r for _, r in scored[:5]]

    evidence = []
    for r in zho_lexical:
        evidence.append({
            "evidence_id": f"ZHO:{r['id']}", "source": "ZHO", "source_authority": "INSTITUTIONAL_UAE_REFERENCE",
            "word_en": r.get("word_en"), "word_ar": r.get("word_ar"), "zho_stable_id": r["id"],
        })
    for i, r in enumerate(esl_candidates):
        evidence.append({
            "evidence_id": f"ESL:{r.get('youtube_video_id')}:{r.get('item_index_in_video')}",
            "source": "ESL_ZAYED", "source_authority": "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE",
            "word_en": r.get("english_meaning_from_video"), "word_ar": r.get("arabic_caption"),
            "youtube_video_id": r.get("youtube_video_id"), "timestamp_index": r.get("item_index_in_video"),
        })
    # de-dup by evidence_id
    seen = set()
    dedup = []
    for e in evidence:
        if e["evidence_id"] not in seen:
            seen.add(e["evidence_id"])
            dedup.append(e)
    return dedup


def evidence_aware_plan_unit(unit, lang, model):
    is_arabic = _looks_arabic(unit["educational_sentence"])
    evidence = build_evidence_for_unit(unit, is_arabic)
    prompt_input = {
        "concept": unit["concept"], "key_terms": unit.get("key_terms", []),
        "educational_sentence": unit["educational_sentence"],
        "evidence": [{k: v for k, v in e.items() if k not in ("zho_stable_id",)} for e in evidence],
    }
    prompt = f"{EVIDENCE_AWARE_SYSTEM_PROMPT}\n\nINPUT:\n{json.dumps(prompt_input, ensure_ascii=False)}\n\nJSON array:"
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {"items": [], "status": "REVIEW_REQUIRED", "reason": str(e), "evidence_supplied": evidence}

    stripped = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    m = re.search(r"\[.*\]", stripped, re.DOTALL)
    parsed = None
    if m:
        try:
            parsed = json.loads(m.group())
        except json.JSONDecodeError:
            parsed = None
    if not isinstance(parsed, list):
        return {"items": [], "status": "REVIEW_REQUIRED", "reason": "unparseable output", "evidence_supplied": evidence, "raw": raw[:500]}

    evidence_by_id = {e["evidence_id"]: e for e in evidence}
    resolved_items = []
    for it in parsed:
        if not isinstance(it, dict) or not it.get("semantic_concept"):
            continue
        concept = str(it["semantic_concept"]).strip()
        eid = it.get("evidence_id")
        if eid in (None, "null", "NONE", "None", ""):
            eid = None
        if eid is not None and eid not in evidence_by_id:
            # PART 11 authority boundary enforcement: any id not in the
            # supplied set is deterministically rejected outright.
            resolved_items.append({"semantic_concept": concept, "render_source": "REJECTED_HALLUCINATED_ID",
                                    "evidence_id_claimed": eid, "verification_status": "REJECTED"})
            continue
        if eid is None:
            # Genuine gap per Falcon's own judgement — run the SAME
            # production fingerspelling fallback as Plan A, for a fair
            # fingerspelling-burden comparison (read-only production reuse).
            term_info = resolve_terminology(concept, lang, unit["source_span"], unit["educational_sentence"], model) \
                if lang == "en" else {"translation_status": "NOT_NEEDED", "arabic_term": concept}
            arabic_term = term_info.get("arabic_term") or concept
            spelled = fingerspell(arabic_term) if arabic_term else {"fully_resolved": False}
            if spelled.get("fully_resolved"):
                resolved_items.append({"semantic_concept": concept, "render_source": "FINGERSPELL",
                                        "arabic_term": arabic_term, "zho": "NOT_FOUND", "esl_zayed": "NOT_FOUND",
                                        "gap_reason": "GENUINE_LEXICAL_GAP", "verification_status": "FINGERSPELL_OK"})
            else:
                resolved_items.append({"semantic_concept": concept, "render_source": "UNSUPPORTED",
                                        "zho": "NOT_FOUND", "esl_zayed": "NOT_FOUND",
                                        "gap_reason": "GENUINE_LEXICAL_GAP", "verification_status": "UNSUPPORTED"})
            continue
        ev = evidence_by_id[eid]
        resolved_items.append({
            "semantic_concept": concept, "render_source": ev["source"], "evidence_id": eid,
            "word_en": ev.get("word_en"), "word_ar": ev.get("word_ar"),
            "supporting_sources": [], "verification_status": "VERIFIED_IN_CANDIDATE_SET",
            "zho_stable_id": ev.get("zho_stable_id"), "youtube_video_id": ev.get("youtube_video_id"),
        })
    return {"items": resolved_items, "status": "OK", "evidence_supplied": evidence, "raw_falcon_output": parsed}


def run_plan_b(understand_concepts, episode_units, lang, model):
    """Re-plans using the SAME grounded units Plan A produced (identical
    concept/source_span/educational_sentence) - only the sign-oriented
    breakdown differs, isolating the planning-strategy variable."""
    t0 = time.time()
    unit_plans = []
    for u in episode_units:
        if not u.get("educational_sentence"):
            unit_plans.append({**u, "plan_b": {"items": [], "status": "REVIEW_REQUIRED", "reason": "no educational_sentence"}})
            continue
        plan = evidence_aware_plan_unit(u, lang, model)
        unit_plans.append({**u, "plan_b": plan})
    return {"units": unit_plans, "elapsed_s": round(time.time() - t0, 1)}


# ---------------------------------------------------------------------
# Metrics (Part 7).
# ---------------------------------------------------------------------
def function_word_count(items, lang):
    fw = FUNCTION_WORDS_AR_HINT if lang == "ar" else FUNCTION_WORDS_EN
    return sum(1 for it in items if str(it).strip().lower() in fw or str(it).strip() in fw)


def metrics_plan_a(units, lang):
    all_res = [r for u in units for r in u.get("sign_resolution", [])]
    plan_items = [it for u in units for it in u.get("semantic_sign_plan", [])]
    verified = [r for r in all_res if r["status"] == STATUS_VERIFIED]
    fingerspelled = [r for r in all_res if r["status"] == STATUS_FINGERSPELL]
    unsupported_review = [r for r in all_res if r["status"] in (STATUS_UNSUPPORTED, STATUS_REVIEW)]
    zho_all = len(verified)  # Plan A's only lexical source IS the ZHO catalog
    return {
        "total_planned_semantic_units": len(plan_items),
        "zho_renderable_units": zho_all,
        "esl_zayed_supported_units": 0,  # Plan A has no ESL Zayed evidence path at all
        "fingerspelled_units": len(fingerspelled),
        "unsupported_or_review_units": len(unsupported_review),
        "unnecessary_function_word_units": function_word_count(plan_items, lang),
        "candidate_selections_rejected_by_verification": sum(
            1 for r in all_res if r.get("retrieval_trace", {}).get("candidates") and r["status"] != STATUS_VERIFIED
        ),
        "provenance_complete_units": zho_all + len(fingerspelled),  # every VERIFIED_SIGN/FINGERSPELL carries a full trace
    }


def metrics_plan_b(unit_plans, lang):
    all_items = [it for u in unit_plans for it in u.get("plan_b", {}).get("items", [])]
    zho = sum(1 for it in all_items if it.get("render_source") == "ZHO")
    esl = sum(1 for it in all_items if it.get("render_source") == "ESL_ZAYED")
    fs = sum(1 for it in all_items if it.get("render_source") == "FINGERSPELL")
    unsupported = sum(1 for it in all_items if it.get("render_source") == "UNSUPPORTED")
    rejected = sum(1 for it in all_items if it.get("render_source") == "REJECTED_HALLUCINATED_ID")
    concepts = [it["semantic_concept"] for it in all_items if it.get("render_source") != "REJECTED_HALLUCINATED_ID"]
    return {
        "total_planned_semantic_units": len(all_items),
        "zho_renderable_units": zho,
        "esl_zayed_supported_units": esl,
        "fingerspelled_units": fs,
        "unsupported_or_review_units": unsupported,
        "unnecessary_function_word_units": function_word_count(concepts, lang),
        "candidate_selections_rejected_by_verification": rejected,
        "provenance_complete_units": zho + esl + fs,
    }


def main():
    all_results = {}
    for case in CASES:
        print(f"\n=== Running case: {case['label']} ===", flush=True)
        lang = detect_language(case["text"])
        plan_a = run_plan_a(case["text"], lang)
        print(f"  Plan A done in {plan_a['elapsed_s']}s, {len(plan_a['units'])} units", flush=True)
        plan_b = run_plan_b(plan_a["understand"]["concepts"], plan_a["units"], lang, MODEL)
        print(f"  Plan B done in {plan_b['elapsed_s']}s", flush=True)

        m_a = metrics_plan_a(plan_a["units"], lang)
        m_b = metrics_plan_b(plan_b["units"], lang)

        all_results[case["id"]] = {
            "label": case["label"], "source_note": case["source_note"], "detected_lang": lang,
            "source_text": case["text"],
            "plan_a": plan_a, "plan_b": plan_b,
            "metrics_plan_a": m_a, "metrics_plan_b": m_b,
        }
        out_path = os.path.join(OUT_DIR, f"case_{case['id']}_20260823.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results[case["id"]], f, ensure_ascii=False, indent=2, default=str)
        print(f"  Wrote {out_path}", flush=True)
        print(f"  Plan A metrics: {m_a}", flush=True)
        print(f"  Plan B metrics: {m_b}", flush=True)

    summary_path = os.path.join(OUT_DIR, "ab_experiment_summary_20260823.json")
    summary = {cid: {"label": v["label"], "metrics_plan_a": v["metrics_plan_a"], "metrics_plan_b": v["metrics_plan_b"]}
               for cid, v in all_results.items()}
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nWrote summary: {summary_path}")


if __name__ == "__main__":
    main()
