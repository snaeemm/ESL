#!/usr/bin/env python3
"""Catalog validation report (final hardening pass, brief §B).

Distinguishes SOURCE DATA problems (anomalies present in ZHO's own
official data - e.g. the Father/Mother/Sister shared Arabic label) from
PIPELINE problems (anything our own crawl/join logic could have caused,
e.g. a duplicate stable id or a row missing its video asset).

Run: .venv/bin/python scripts/zho_catalog_validation_report.py
Writes: data/zho/catalog_validation_report.json (does NOT modify or
overwrite catalog.json or the existing catalog_bilingual_report.json -
this is a read-only report generator).
"""
import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")
OUT_PATH = os.path.join(ROOT, "data", "zho", "catalog_validation_report.json")


def main():
    rows = json.load(open(CATALOG_PATH, encoding="utf-8"))
    total = len(rows)

    en_present = [r for r in rows if r.get("word_en")]
    ar_present = [r for r in rows if r.get("word_ar")]
    both = [r for r in rows if r.get("word_en") and r.get("word_ar")]
    en_only = [r for r in rows if r.get("word_en") and not r.get("word_ar")]
    ar_only = [r for r in rows if r.get("word_ar") and not r.get("word_en")]
    missing_en = [r for r in rows if not r.get("word_en")]
    missing_ar = [r for r in rows if not r.get("word_ar")]

    id_counts = collections.Counter(r["id"] for r in rows)
    dup_ids = {k: v for k, v in id_counts.items() if v > 1}

    vimeo_counts = collections.Counter(r["vimeo_id"] for r in rows if r.get("vimeo_id"))
    dup_vimeo = {k: v for k, v in vimeo_counts.items() if v > 1}
    # which word_en/word_ar labels share a duplicated vimeo id (this is
    # the class of anomaly the brief's Father/Mother/Sister example is)
    dup_vimeo_detail = {}
    if dup_vimeo:
        by_vimeo = collections.defaultdict(list)
        for r in rows:
            if r.get("vimeo_id") in dup_vimeo:
                by_vimeo[r["vimeo_id"]].append({"id": r["id"], "word_en": r.get("word_en"), "word_ar": r.get("word_ar")})
        dup_vimeo_detail = dict(by_vimeo)

    en_label_counts = collections.Counter(r["word_en"].strip().lower() for r in rows if r.get("word_en"))
    dup_en_labels = {k: v for k, v in en_label_counts.items() if v > 1}

    ar_label_counts = collections.Counter(r["word_ar"].strip() for r in rows if r.get("word_ar"))
    dup_ar_labels = {k: v for k, v in ar_label_counts.items() if v > 1}
    # Rows whose word_ar is shared by >1 distinct English concept, e.g.
    # Father/Mother/Sister all mapping to the official ZHO label
    # "باب الأسرة" - this is a SOURCE DATA anomaly (ZHO's own title data),
    # not something our join logic introduced or should silently correct.
    ambiguous_ar_labels = {}
    if dup_ar_labels:
        by_ar = collections.defaultdict(list)
        for r in rows:
            if (r.get("word_ar") or "").strip() in dup_ar_labels:
                by_ar[r["word_ar"].strip()].append({"id": r["id"], "word_en": r.get("word_en")})
        # only keep ones where the EN labels are actually distinct concepts
        ambiguous_ar_labels = {
            ar: ens for ar, ens in by_ar.items()
            if len({e["word_en"] for e in ens}) > 1
        }

    missing_video = [r for r in rows if not r.get("has_video")]
    missing_thumb = [r for r in rows if not r.get("thumb_path")]

    report = {
        "generated_by": "scripts/zho_catalog_validation_report.py",
        "totals": {
            "total_rows": total,
            "en_records": len(en_present),
            "ar_records": len(ar_present),
            "bilingual_joins_both_labels": len(both),
            "en_only": len(en_only),
            "ar_only": len(ar_only),
            "missing_en_labels": len(missing_en),
            "missing_ar_labels": len(missing_ar),
            "missing_video_asset": len(missing_video),
            "missing_thumbnail": len(missing_thumb),
        },
        "pipeline_quality_checks": {
            "duplicate_stable_ids": dup_ids,
            "duplicate_stable_ids_note": (
                "Duplicate `id` values would indicate a PIPELINE bug (the crawler/join produced two rows for "
                "the same stable Sitecore item) - none found is the expected/healthy result."
            ),
            "rows_missing_video_asset": [{"id": r["id"], "word_en": r.get("word_en")} for r in missing_video],
            "rows_missing_video_note": "PIPELINE/crawl-completeness issue if any - these rows cannot be used as verified signs (has_video gate in lib/sign_resolver.py already excludes them).",
        },
        "source_data_quality_anomalies": {
            "missing_en_labels": [r["id"] for r in missing_en],
            "missing_ar_labels_count": len(missing_ar),
            "missing_ar_labels_note": (
                "6 catalog entries have no official ZHO Arabic label (2 have no Arabic counterpart row at all, "
                "4 matched by stable id but the Arabic-locale title field itself was empty in ZHO's data). "
                "Preserved as missing, per instruction, rather than machine-translated or fabricated - see "
                "data/zho/catalog_bilingual_report.json for the exact rows."
            ),
            "duplicate_video_ids_shared_by_multiple_labels": dup_vimeo_detail,
            "duplicate_english_labels": dup_en_labels,
            "duplicate_arabic_labels_ambiguous_join": ambiguous_ar_labels,
            "duplicate_arabic_labels_note": (
                "These are SOURCE DATA anomalies (ZHO's own official title data), not something introduced by "
                "our stable-id join or corrected/hidden by our pipeline. Known example: Father/Mother/Sister "
                "(and potentially other family-relation entries) can share the identical official Arabic title "
                "'باب الأسرة' despite being distinct English concepts with distinct stable ids and distinct video "
                "assets - the resolver still resolves each one correctly by stable id + video, but an "
                "EXACT_AR text lookup on that shared label alone would be genuinely ambiguous between them. "
                "Not rewritten to look cleaner, per instruction."
            ),
        },
        "ambiguous_joins": {
            "description": (
                "A join is 'ambiguous' if a single normalized Arabic (or English) label text maps to more than "
                "one distinct stable id - see duplicate_arabic_labels_ambiguous_join above. The resolver's exact "
                "match (lib/vocab_retrieval.py exact_match) always returns the FIRST catalog-order match for a "
                "shared label; downstream code never disambiguates by anything other than the stable id/video, "
                "so an ambiguous label is a genuine, disclosed limitation of pure exact-AR-text lookup, not "
                "silently resolved by guessing."
            ),
        },
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_PATH}")
    print(json.dumps(report["totals"], indent=2))
    print(f"duplicate_arabic_labels_ambiguous_join count: {len(ambiguous_ar_labels)}")
    print(f"duplicate_video_ids count: {len(dup_vimeo_detail)}")
    print(f"duplicate_english_labels count: {len(dup_en_labels)}")


if __name__ == "__main__":
    main()
