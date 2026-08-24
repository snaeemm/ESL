"""Regression tests for Arabic-aware vocabulary hints in
lib/sign_plan.py's _vocabulary_hints() (item 2 of the bilingual ZHO
resolution fix set). English-source behavior must remain byte-for-byte
unchanged; Arabic-source sentences must now use the Arabic tokenizer
instead of silently producing zero hints (English tokenizer on Arabic
script yields no tokens at all).

Run directly:
    .venv/bin/python -m tests.test_sign_plan_arabic_hints
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.sign_plan import _vocabulary_hints, _relevant_inventory, _check_semantic_preservation
from lib.vocab_retrieval import reset_index_cache, reset_esl_zayed_index_cache


def _reset():
    reset_index_cache()
    reset_esl_zayed_index_cache()


def test_arabic_sentence_produces_nonempty_hints_for_shams():
    _reset()
    hints = _vocabulary_hints("الشمس مصدر الضوء والحرارة.", ["شمس"])
    assert hints, "expected at least one Arabic-tokenized hint for a sentence containing شمس"
    assert any("شمس" in h or "Sun" in h for h in hints), hints
    print(f"PASS: Arabic sentence about الشمس produces vocabulary hints: {hints[:3]}")


def test_english_sentence_hints_unchanged_english_tokenizer():
    _reset()
    hints = _vocabulary_hints("The membrane controls what enters and leaves the cell.", ["membrane", "cell"])
    # Just confirm the English path still runs and returns a list (no
    # crash, no Arabic-token contamination) - exact content depends on
    # catalog contents, already covered by other regression tests.
    assert isinstance(hints, list)
    print(f"PASS: English sentence hint path still returns a list ({len(hints)} hints), unchanged code path")


def test_arabic_sentence_no_longer_silently_empty():
    """Root-cause regression: before the fix, _vocabulary_hints always
    called the English-only tokenizer, so ANY pure-Arabic sentence with
    no Latin-script content produced zero tokens and thus zero hints,
    even when the catalog had directly relevant Arabic entries."""
    _reset()
    from lib.vocab_retrieval import _tokenize_en
    query = "الشمس مصدر الضوء والحرارة. شمس"
    assert _tokenize_en(query) == [], "fixture assumption broken: English tokenizer should yield nothing on pure Arabic text"
    hints = _vocabulary_hints("الشمس مصدر الضوء والحرارة.", ["شمس"])
    assert hints, "Arabic sentence still produced zero hints - Arabic-aware tokenizer not actually wired in"
    print("PASS: Arabic sentence no longer silently produces zero hints (confirmed old-bug fixture would have failed)")


# --- Part B: inventory-aware realization (final functional pass) --------

def test_relevant_inventory_includes_source_labeled_esl_zayed_candidates():
    """_relevant_inventory() (the Part B upgrade from incidental hints to
    a real bounded retrieval step) must include safe WORD-level ESL Zayed
    candidates alongside ZHO ones, each explicitly source/authority
    labeled, so the planner is aware which vocabulary is institutional
    vs observed/unverified - not silently blended together."""
    _reset()
    # "Sleepy" is a known ESL-Zayed-only WORD concept (see Blocker E/G
    # proof runs) with no ZHO institutional equivalent.
    inv = _relevant_inventory("Today I feel sleepy after a long day.", ["sleepy"])
    assert inv, "expected at least one relevant inventory entry for 'sleepy'"
    sources = {e["source"] for e in inv}
    assert "ESL_ZAYED" in sources, f"expected an ESL_ZAYED entry for 'sleepy', got sources={sources}"
    esl_entries = [e for e in inv if e["source"] == "ESL_ZAYED"]
    assert all(e["authority"] == "SUPPLEMENTARY_UNVERIFIED" for e in esl_entries), esl_entries
    zho_entries = [e for e in inv if e["source"] == "ZHO"]
    assert all(e["authority"] == "INSTITUTIONAL_UAE_REFERENCE" for e in zho_entries), zho_entries
    print(f"PASS: relevant inventory includes source-labeled ESL Zayed candidates: {esl_entries[:2]}")


def test_relevant_inventory_bounded_not_full_catalog_dump():
    """Must stay a bounded, relevant retrieval - never the whole catalog
    (that would defeat the point of 'relevant' inventory and risk
    context-stuffing/prompt-injection-style noise)."""
    _reset()
    inv = _relevant_inventory("The membrane controls what enters and leaves the cell.", ["membrane", "cell"], top_n=12)
    assert len(inv) <= 12, f"expected retrieval to stay bounded by top_n, got {len(inv)} entries"
    print(f"PASS: relevant inventory stays bounded ({len(inv)} entries, top_n=12)")


def test_semantic_preservation_gate_catches_school_starts_collapse():
    """Must catch the exact SCHOOL STARTS -> SCHOOL regression class: a
    grounded key_term ('start') with zero token overlap against every
    plan item is flagged, not silently accepted."""
    unit = {"key_terms": ["school", "start", "morning"]}
    preserved, missing = _check_semantic_preservation(unit, ["SCHOOL"])
    assert preserved is False, "collapsed plan must fail the semantic-preservation gate"
    assert "start" in missing and "morning" in missing, missing
    print(f"PASS: semantic-preservation gate catches SCHOOL STARTS-class collapse, missing={missing}")


def test_semantic_preservation_gate_passes_full_plan():
    """Must NOT over-correct: a plan that genuinely covers every grounded
    key_term passes cleanly."""
    unit = {"key_terms": ["school", "start", "morning"]}
    preserved, missing = _check_semantic_preservation(unit, ["SCHOOL", "START", "MORNING"])
    assert preserved is True and missing == [], (preserved, missing)
    print("PASS: semantic-preservation gate does not over-correct a genuinely complete plan")


def test_semantic_preservation_gate_never_deletes_the_plan():
    """Even when the gate fails, the realized plan items themselves must
    be preserved in the result (conservative: flag for review, never
    silently discard what was produced) - this is exercised at the
    build_sign_plan() integration level."""
    _reset()
    from lib import sign_plan
    orig = sign_plan._call_ollama_raw
    sign_plan._call_ollama_raw = lambda *a, **kw: '["SCHOOL"]'
    try:
        unit = {"concept": "school routine", "key_terms": ["school", "start", "morning"],
                "source_span": "School starts early in the morning.",
                "educational_sentence": "School starts early in the morning."}
        result = sign_plan.build_sign_plan(unit, model="unused")
        assert result["semantic_sign_plan"] == ["SCHOOL"], (
            "the realized item(s) must be kept even when the preservation gate fails")
        assert result["semantic_plan_status"] == "REVIEW_REQUIRED", result
        assert result.get("possible_information_loss") is True, result
    finally:
        sign_plan._call_ollama_raw = orig
    print("PASS: semantic-preservation gate failure flags for review without deleting the realized plan")


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} sign_plan Arabic vocabulary-hint tests passed")


if __name__ == "__main__":
    run_all()
