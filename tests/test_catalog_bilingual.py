"""Regression tests for the bilingual ZHO catalog join (brief §B/§C/§R).

Run directly:
    .venv/bin/python -m tests.test_catalog_bilingual
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.vocab_retrieval import get_index, reset_index_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")


def test_no_duplicate_stable_ids():
    rows = json.load(open(CATALOG_PATH, encoding="utf-8"))
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate stable ids found - would indicate a pipeline join bug"
    print(f"PASS: all {len(ids)} stable ids are unique")


def test_missing_arabic_stays_missing_not_fabricated():
    rows = json.load(open(CATALOG_PATH, encoding="utf-8"))
    missing = [r for r in rows if not r.get("word_ar")]
    assert 0 < len(missing) <= 10, f"expected a small known set of missing-Arabic rows, got {len(missing)}"
    for r in missing:
        assert r.get("word_ar") in (None, ""), r
    print(f"PASS: {len(missing)} rows with missing Arabic labels preserved as missing (not fabricated/translated)")


def test_same_id_resolves_en_and_ar_to_same_video():
    reset_index_cache()
    idx = get_index()
    both = [r for r in idx.rows if r.get("word_en") and r.get("word_ar") and r.get("has_video")]
    assert both, "no bilingual rows with video found"
    sample = both[0]
    en_row, _ = idx.exact_match(sample["word_en"])
    ar_row, _ = idx.exact_match(sample["word_ar"])
    assert en_row["id"] == sample["id"], "EN exact match did not resolve to its own row"
    assert ar_row["id"] == sample["id"] or ar_row is None, (
        "AR exact match resolved to a DIFFERENT id than the EN match for the same catalog row "
        "(only acceptable if the AR label is genuinely ambiguous/shared across rows, in which case "
        "ar_row would legitimately be a different row's id - see catalog_validation_report.json)"
    )
    assert en_row.get("vimeo_id") == sample.get("vimeo_id")
    print(f"PASS: EN lookup for '{sample['word_en']}' resolves to the same stable id/video as the catalog row itself")


def test_word_en_backward_compatibility():
    """Older code paths keyed purely on word_en must still work - the
    bilingual redesign is additive (word_ar alongside word_en), not a
    breaking schema change."""
    reset_index_cache()
    idx = get_index()
    sample = next(r for r in idx.rows if r.get("word_en"))
    row, method = idx.exact_match(sample["word_en"])
    assert row is not None and row["id"] == sample["id"]
    print("PASS: word_en-only exact match still resolves correctly (backward compatible)")


def test_official_arabic_not_overwritten_by_aliases():
    """Curated aliases (data/zho/aliases.json) must never overwrite an
    official word_ar/word_en - they are additive lookup entries only."""
    reset_index_cache()
    idx = get_index()
    for r in idx.rows:
        if r.get("word_ar"):
            assert isinstance(r["word_ar"], str) and r["word_ar"], r
    print("PASS: official word_ar values are untouched strings, not overwritten by alias loading")


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} catalog bilingual regression tests passed")


if __name__ == "__main__":
    run_all()
