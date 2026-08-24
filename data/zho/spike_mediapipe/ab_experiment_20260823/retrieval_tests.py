"""SCRATCH / EXPERIMENTAL — Parts 2 & 3: MiniLM lexical retrieval over
ZHO + ESL Zayed, and a bounded hand-checked sentence/phrase retrieval
sanity test. Read-only against production lib/ code (imports
lib.vocab_embedding_st, does not modify it). Uses MiniLM only (the
already-benchmark-selected model) — no new embedding-model bake-off.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, ROOT)
SPIKE_DIR = os.path.join(ROOT, "data", "zho", "spike_mediapipe")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def build_esl_lexical_index(model, full_corpus):
    """WORD-type ESL Zayed records only (lexical, matches ZHO's own
    granularity) — PHRASE/SENTENCE handled separately in the sentence test."""
    rows = [r for r in full_corpus if r.get("content_type") == "WORD" and r.get("english_meaning_from_video")]
    texts = [f"{r['english_meaning_from_video']} | {r.get('arabic_caption','')}" for r in rows]
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return rows, vecs


def build_zho_index(model):
    with open(os.path.join(ROOT, "data", "zho", "catalog.json"), encoding="utf-8") as f:
        rows = [r for r in json.load(f) if r.get("word_en")]
    texts = [f"{r.get('word_en','')} | {r.get('word_ar','')} | {r.get('category','')}" for r in rows]
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return rows, vecs


def topk(model, query, rows, vecs, k=5):
    qv = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
    sims = vecs @ qv
    order = np.argsort(-sims)[:k]
    return [(round(float(sims[i]), 4), rows[i]) for i in order]


def part2_lexical_retrieval(model, zho_rows, zho_vecs, esl_rows, esl_vecs):
    """Grounded test concepts drawn from the five A/B case topics (family,
    school, biology-adjacent ordinary vocabulary, dialect vocabulary) —
    confirms retrieval CAN surface real evidence from either corpus for a
    grounded concept, with full provenance per item (task Part 2)."""
    test_concepts = [
        "father", "mother", "sister", "brother", "school", "teacher", "book",
        "sun", "hot", "cold", "winter", "summer", "happy", "eat", "walk",
        "sick", "tired", "family", "home", "morning",
    ]
    findings = []
    for q in test_concepts:
        zho_hits = topk(model, q, zho_rows, zho_vecs, k=3)
        esl_hits = topk(model, q, esl_rows, esl_vecs, k=3)
        findings.append({
            "query": q,
            "zho_top3": [
                {"source": "ZHO", "source_authority": "INSTITUTIONAL_UAE_REFERENCE",
                 "record_id": r["id"], "word_en": r.get("word_en"), "word_ar": r.get("word_ar"),
                 "similarity": s, "retrieval_reason": "MiniLM cosine similarity, top-k"}
                for s, r in zho_hits
            ],
            "esl_zayed_top3": [
                {"source": "ESL_ZAYED", "source_authority": "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE",
                 "youtube_video_id": r.get("youtube_video_id"), "english_meaning": r.get("english_meaning_from_video"),
                 "arabic_caption": r.get("arabic_caption"), "similarity": s,
                 "retrieval_reason": "MiniLM cosine similarity, top-k"}
                for s, r in esl_hits
            ],
        })
    return findings


# Part 3 — bounded, hand-checked phrase/sentence sanity test. 16 test
# planning "meanings" (drawn from realistic lesson content: family/school
# register, matching the five A/B cases' domain), each hand-labeled with
# which of the 45 PHRASE + 6 SENTENCE + 1 DIALOGUE_OR_SEQUENCE ESL Zayed
# observed examples (by english_meaning_from_video, matched against the
# actual corpus at run time) should be RELEVANT / POSSIBLY_RELEVANT /
# IRRELEVANT. Hand judgments were made by reading the actual 52
# phrase/sentence/dialogue records in esl_zayed_full_93video_corpus once
# (bounded — this bucket is small enough to read in full), then written
# down BEFORE running retrieval below.
TEST_MEANINGS = [
    {"meaning": "greeting someone", "relevant_substrings": ["salaam", "hello", "how are you", "peace"]},
    {"meaning": "asking someone's name", "relevant_substrings": ["what is your name", "my name is"]},
    {"meaning": "family member relationship", "relevant_substrings": ["book", "family"]},  # weak/negative control
    {"meaning": "expressing thanks", "relevant_substrings": ["thank you", "thanks"]},
    {"meaning": "saying goodbye", "relevant_substrings": ["goodbye", "bye", "see you"]},
    {"meaning": "talking about feeling sick", "relevant_substrings": ["sick", "tired", "not feeling well"]},
    {"meaning": "asking for help", "relevant_substrings": ["help me", "can you help"]},
    {"meaning": "talking about school subjects", "relevant_substrings": ["school", "study", "class"]},
    {"meaning": "describing the weather", "relevant_substrings": ["hot", "cold", "weather", "rain"]},
    {"meaning": "counting or numbers in a sentence", "relevant_substrings": ["how old", "age", "number"]},
    {"meaning": "talking about eating a meal", "relevant_substrings": ["eat", "food", "hungry"]},
    {"meaning": "apologizing", "relevant_substrings": ["sorry", "excuse me"]},
    {"meaning": "asking where something is", "relevant_substrings": ["where", "location"]},
    {"meaning": "wishing someone well/congratulations", "relevant_substrings": ["congratulations", "happy", "blessing"]},
    {"meaning": "introducing yourself", "relevant_substrings": ["my name", "i am", "nice to meet"]},
    {"meaning": "talking about photosynthesis", "relevant_substrings": []},  # negative control: no real ESL Zayed evidence expected
]


def part3_sentence_sanity(model, phrase_rows, phrase_vecs):
    results = []
    hits1 = hits5 = scored1 = scored5 = 0
    for tc in TEST_MEANINGS:
        hits = topk(model, tc["meaning"], phrase_rows, phrase_vecs, k=5)
        rel_subs = tc["relevant_substrings"]
        has_expected_evidence = len(rel_subs) > 0
        def is_relevant(text):
            t = (text or "").lower()
            return any(s in t for s in rel_subs)
        top1_relevant = is_relevant(hits[0][1].get("english_meaning_from_video")) if hits else False
        top5_relevant = any(is_relevant(r.get("english_meaning_from_video")) for _, r in hits)
        if has_expected_evidence:
            scored1 += 1
            scored5 += 1
            hits1 += int(top1_relevant)
            hits5 += int(top5_relevant)
        results.append({
            "meaning": tc["meaning"], "has_expected_evidence_in_corpus": has_expected_evidence,
            "top5": [
                {"english_meaning": r.get("english_meaning_from_video"), "video_id": r.get("youtube_video_id"),
                 "content_type": r.get("content_type"), "similarity": s}
                for s, r in hits
            ],
            "top1_relevant": top1_relevant if has_expected_evidence else "N/A (negative control)",
            "top5_relevant": top5_relevant if has_expected_evidence else "N/A (negative control)",
        })
    recall1 = round(hits1 / scored1, 3) if scored1 else None
    recall5 = round(hits5 / scored5, 3) if scored5 else None
    return {
        "n_test_meanings": len(TEST_MEANINGS), "n_scored_positive_controls": scored1,
        "recall_at_1": recall1, "recall_at_5": recall5, "per_case": results,
    }


def main():
    with open(os.path.join(SPIKE_DIR, "esl_zayed_full_93video_corpus_20260823.json"), encoding="utf-8") as f:
        full_corpus = json.load(f)

    model = SentenceTransformer(MODEL_NAME)
    zho_rows, zho_vecs = build_zho_index(model)
    esl_rows, esl_vecs = build_esl_lexical_index(model, full_corpus)

    part2 = part2_lexical_retrieval(model, zho_rows, zho_vecs, esl_rows, esl_vecs)

    phrase_rows = [r for r in full_corpus
                   if r.get("content_type") in ("PHRASE", "SENTENCE", "DIALOGUE_OR_SEQUENCE")
                   and r.get("english_meaning_from_video")]
    phrase_texts = [f"{r['english_meaning_from_video']} | {r.get('arabic_caption','')}" for r in phrase_rows]
    phrase_vecs = model.encode(phrase_texts, normalize_embeddings=True, show_progress_bar=False)
    part3 = part3_sentence_sanity(model, phrase_rows, phrase_vecs)

    verdict = "NOT_USEFUL"
    if part3["recall_at_1"] is not None:
        if part3["recall_at_1"] >= 0.6:
            verdict = "SUITABLE"
        elif part3["recall_at_5"] and part3["recall_at_5"] >= 0.6:
            verdict = "LIMITED_BUT_USEFUL"
        else:
            verdict = "NOT_USEFUL"

    out = {
        "model_used": MODEL_NAME,
        "part2_lexical_retrieval_zho_and_esl": part2,
        "part3_sentence_phrase_sanity_test": part3,
        "part3_verdict": verdict,
        "n_phrase_sentence_dialogue_records_in_corpus": len(phrase_rows),
    }
    out_path = os.path.join(OUT_DIR, "retrieval_test_results_20260823.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")
    print("Part3 recall@1:", part3["recall_at_1"], "recall@5:", part3["recall_at_5"], "verdict:", verdict)


if __name__ == "__main__":
    main()
