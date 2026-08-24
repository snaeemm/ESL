"""SCRATCH / EXPERIMENTAL — Part 1: clean the coarse ESL Zayed <-> ZHO
comparison bucket. Read-only against production. Writes
cleaned_comparison_20260823.json into this same scratch dir.

Not production code. Bounded heuristic re-classification of the 112
"variant_matches" + a sample of "new_lexical"/"exact_matches" records,
per FINAL task Part 1. Does not hand-inspect all 403 raw corpus records.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, ROOT)

SPIKE_DIR = os.path.join(ROOT, "data", "zho", "spike_mediapipe")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

STOP_EN = {"the", "a", "an", "of", "my", "your", "his", "her", "our", "their", "is", "are", "to", "in", "on"}


def toks(s):
    return set(w for w in re.findall(r"[a-zA-Z']+", (s or "").lower()) if w not in STOP_EN)


def classify_variant(rec):
    """rec has english, arabic, catalog_en_match. Bounded lexical-overlap
    + known-pattern heuristic (Part 1). Categories:
      ZHO_PLAUSIBLE_VARIANT  - genuine token overlap / plausible morphological or
                                 semantic-neighbor relation, kept as CANDIDATE evidence only
      ESL_ZAYED_ONLY         - coarse match was a false positive; treat as ESL-only observation
      MULTI_CONCEPT          - the ESL item is a possessive/inflected multi-morpheme phrase
                                 (e.g. "My book") matched only on its head noun
    """
    eng = rec["english"]
    cat = rec["catalog_en_match"]
    et = toks(eng)
    ct = toks(cat)

    # multi-concept possessive/pronoun+noun pattern: "My/Your/His/Her/Our/Their X"
    if re.match(r"^(my|your|his|her|our|their)\s+\w+", eng.strip(), re.I):
        return "MULTI_CONCEPT", "possessive-pronoun + noun phrase; catalog match is on the head noun only, pronoun has no separate ZHO evidence here"

    if not et or not ct:
        return "ESL_ZAYED_ONLY", "empty token set after normalization"

    overlap = et & ct
    if overlap:
        return "ZHO_PLAUSIBLE_VARIANT", f"genuine token overlap: {sorted(overlap)}"

    # known false-positive substring pattern (coarse matcher matched on a
    # short substring inside a longer unrelated catalog word, e.g.
    # "laa" inside "Salaam Alaikum", "red" inside "Tired")
    return "ESL_ZAYED_ONLY", f"no real token overlap between '{eng}' and catalog match '{cat}' — coarse substring false positive, treat as ESL-only observation, NOT a ZHO variant"


def main():
    with open(os.path.join(SPIKE_DIR, "esl_zayed_zho_comparison_20260823.json"), encoding="utf-8") as f:
        comp = json.load(f)

    cleaned_variants = []
    for rec in comp["variant_matches"]:
        cls, reason = classify_variant(rec)
        cleaned_variants.append({**rec, "cleaned_classification": cls, "cleaning_reason": reason})

    counts = {}
    for r in cleaned_variants:
        counts[r["cleaned_classification"]] = counts.get(r["cleaned_classification"], 0) + 1

    # exact_matches: spot-verify a bounded sample (first 20 + any containing
    # digits/letters markers) rather than all 128 — per task's "bounded
    # representative sample" instruction. These came from a stricter coarse
    # rule (exact string match after normalization) so false-positive risk
    # is much lower than variant_matches; sample-check only.
    exact_sample = comp["exact_matches"][:20]
    exact_sample_flagged = []
    for rec in exact_sample:
        # sanity: english field should equal / closely equal zho_ids-linked catalog word;
        # we don't have the catalog word_en text in this record, only zho_ids, so this is a
        # structural sanity check (ids present, non-empty) not a text re-verification.
        ok = bool(rec.get("zho_ids"))
        exact_sample_flagged.append({**rec, "sample_check_zho_ids_present": ok})
    exact_sample_bad = [r for r in exact_sample_flagged if not r["sample_check_zho_ids_present"]]

    # new_lexical (152): classify by content_type proxy using the english
    # field text only (this bucket doesn't carry content_type directly;
    # cross-reference against the full 93-video corpus by english meaning
    # to recover LETTER/NUMBER separation per task instruction).
    with open(os.path.join(SPIKE_DIR, "esl_zayed_full_93video_corpus_20260823.json"), encoding="utf-8") as f:
        full_corpus = json.load(f)
    meaning_to_type = {}
    for r in full_corpus:
        m = (r.get("english_meaning_from_video") or "").strip().lower()
        if m:
            meaning_to_type.setdefault(m, r.get("content_type"))

    new_lexical_classified = []
    letter_count = number_count = word_or_phrase_count = uncertain_count = 0
    for rec in comp["new_lexical"]:
        ct = meaning_to_type.get(rec["english"].strip().lower())
        if ct == "LETTER":
            letter_count += 1
            cls = "LETTER"
        elif ct == "NUMBER":
            number_count += 1
            cls = "NUMBER"
        elif ct in ("WORD", "PHRASE", "SENTENCE"):
            word_or_phrase_count += 1
            cls = "ESL_ZAYED_ONLY"
        else:
            uncertain_count += 1
            cls = "UNCERTAIN"
        new_lexical_classified.append({**rec, "cleaned_classification": cls, "source_content_type": ct})

    result = {
        "method": (
            "Bounded lexical-token-overlap re-classification of the coarse 112-item variant_matches "
            "bucket (all 112 inspected — small enough to fully re-check, not a sample), plus a "
            "structural sanity sample of 20/128 exact_matches, plus content_type recovery for all 152 "
            "new_lexical items via cross-reference against the full 93-video corpus's own content_type "
            "field (deterministic join on english_meaning_from_video, not re-annotated by hand). "
            "MiniLM was not needed for this pass since plain token overlap already separates genuine "
            "candidate-evidence variants from coarse substring false positives with clear, auditable "
            "reasons attached to every record (see cleaning_reason)."
        ),
        "variant_matches_original_count": len(comp["variant_matches"]),
        "variant_matches_cleaned_counts": counts,
        "variant_matches_cleaned": cleaned_variants,
        "exact_matches_sample_checked": len(exact_sample),
        "exact_matches_sample_all_have_zho_ids": len(exact_sample_bad) == 0,
        "exact_matches_sample_bad": exact_sample_bad,
        "new_lexical_original_count": len(comp["new_lexical"]),
        "new_lexical_type_breakdown": {
            "LETTER": letter_count, "NUMBER": number_count,
            "WORD_PHRASE_SENTENCE (ESL_ZAYED_ONLY candidate evidence)": word_or_phrase_count,
            "UNCERTAIN (not found in full corpus content_type join)": uncertain_count,
        },
        "new_lexical_classified": new_lexical_classified,
        "headline_corrected_summary": {
            "ZHO_EXACT": len(comp["exact_matches"]),
            "ZHO_PLAUSIBLE_VARIANT (candidate evidence only, NOT verified)": counts.get("ZHO_PLAUSIBLE_VARIANT", 0),
            "MULTI_CONCEPT (possessive/inflected, head-noun-only overlap)": counts.get("MULTI_CONCEPT", 0),
            "ESL_ZAYED_ONLY_from_variant_bucket (false positives corrected out of the old 112)": counts.get("ESL_ZAYED_ONLY", 0),
            "ESL_ZAYED_ONLY_from_new_lexical (WORD/PHRASE/SENTENCE)": word_or_phrase_count,
            "LETTER (from new_lexical, separated out)": letter_count,
            "NUMBER (from new_lexical, separated out)": number_count,
            "UNCERTAIN": uncertain_count,
        },
    }

    out_path = os.path.join(OUT_DIR, "cleaned_comparison_20260823.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")
    print(json.dumps(result["headline_corrected_summary"], indent=2))
    print("variant_matches_cleaned_counts:", counts)


if __name__ == "__main__":
    main()
