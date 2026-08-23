"""Regression tests for bounded structured-output handling (brief §L/§R).

Mocks only the Ollama network call (`lib.understand._call_ollama`) - the
parse/extraction/schema-validation/repair-retry logic under test is real.

Run directly:
    .venv/bin/python -m tests.test_understand_structured_output
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import understand as u


def _with_mocked_ollama(responses):
    """responses: list of strings returned by successive _call_ollama
    calls (1st = initial, 2nd = repair retry if triggered)."""
    calls = {"n": 0}
    orig = u._call_ollama

    def fake(source_text, model):
        i = calls["n"]
        calls["n"] += 1
        return responses[min(i, len(responses) - 1)]

    u._call_ollama = fake
    return orig, calls


def test_valid_json_no_retry_needed():
    orig, calls = _with_mocked_ollama([
        '[{"concept": "Cell", "key_terms": ["cell"], "source_span": "A cell is the basic unit."}]'
    ])
    try:
        result = u.extract_concepts("A cell is the basic unit.")
        assert result["json_parsed_successfully"]
        assert result["num_concepts_extracted"] == 1
        assert result["structured_output_trace"]["repair_retry_attempted"] is False
        assert calls["n"] == 1, "must not call the model twice when the first response is already valid"
    finally:
        u._call_ollama = orig
    print("PASS: valid JSON parses without a repair retry")


def test_json_surrounded_by_harmless_text_extracted():
    orig, calls = _with_mocked_ollama([
        'Sure, here is the array:\n[{"concept": "Cell", "key_terms": ["cell"], "source_span": "A cell is the basic unit."}]\nHope that helps!'
    ])
    try:
        result = u.extract_concepts("A cell is the basic unit.")
        assert result["json_parsed_successfully"]
        assert result["num_concepts_extracted"] == 1
        assert result["structured_output_trace"]["initial_extraction_used"] is True
        assert result["structured_output_trace"]["repair_retry_attempted"] is False
    finally:
        u._call_ollama = orig
    print("PASS: JSON surrounded by harmless model text is extracted without a retry")


def test_malformed_json_triggers_one_bounded_repair_then_succeeds():
    orig, calls = _with_mocked_ollama([
        '[{"concept": "ذهاب_إلى_الم\'./school", "key_terms": ["نروح"]]',  # malformed, matches real observed failure
        '[]',  # repair retry response
    ])
    try:
        result = u.extract_concepts("مدرستنا بعيدة.")
        trace = result["structured_output_trace"]
        assert trace["initial_parse_success"] is False
        assert trace["repair_retry_attempted"] is True
        assert trace["final_parse_status"] == "OK_AFTER_REPAIR"
        assert result["json_parsed_successfully"] is True
        assert result["num_concepts_extracted"] == 0
        assert calls["n"] == 2, "exactly one repair retry, not an unbounded loop"
    finally:
        u._call_ollama = orig
    print("PASS: malformed JSON triggers exactly one bounded repair retry, then completes deterministically")


def test_malformed_json_after_repair_still_fails_deterministically():
    orig, calls = _with_mocked_ollama([
        'not json at all',
        'still not json',
    ])
    try:
        result = u.extract_concepts("some source text")
        trace = result["structured_output_trace"]
        assert trace["repair_retry_attempted"] is True
        assert trace["final_parse_status"] == "FAILED_AFTER_REPAIR"
        assert result["json_parsed_successfully"] is False
        assert result["num_concepts_extracted"] == 0
        assert calls["n"] == 2, "must stop after exactly one retry, never loop unboundedly"
    finally:
        u._call_ollama = orig
    print("PASS: still-invalid output after the bounded retry fails deterministically (no infinite loop)")


def test_schema_violation_treated_as_invalid():
    """A structurally-parseable array with the wrong shape (e.g. key_terms
    as a string instead of a list) must be treated as invalid, not
    silently passed through with bad data."""
    orig, calls = _with_mocked_ollama([
        '[{"concept": "Cell", "key_terms": "cell", "source_span": "A cell is the basic unit."}]',
        '[]',
    ])
    try:
        result = u.extract_concepts("A cell is the basic unit.")
        assert result["structured_output_trace"]["initial_schema_valid"] is False
        assert result["structured_output_trace"]["repair_retry_attempted"] is True
    finally:
        u._call_ollama = orig
    print("PASS: schema-violating JSON (wrong field types) is rejected, not silently trusted")


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} understand structured-output tests passed")


if __name__ == "__main__":
    run_all()
