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

from lib.sign_plan import _vocabulary_hints
from lib.vocab_retrieval import reset_index_cache


def _reset():
    reset_index_cache()


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


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} sign_plan Arabic vocabulary-hint tests passed")


if __name__ == "__main__":
    run_all()
