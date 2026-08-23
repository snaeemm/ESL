"""Regression tests for the final-hardening pass (brief §H/§I/§J/§R).

Plain assert-based script (no pytest dependency in this environment) -
run directly:

    .venv/bin/python -m tests.test_resolver_regressions

Mocks are used only around the Falcon/Ollama network boundary
(`lib.sign_resolver._call_falcon_candidate_selection`), never around the
deterministic logic under test (morphology tiering, information-loss
classification, verification-set enforcement) - per the brief's own rule
that mocking every function and asserting the mock is not a real test.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import sign_resolver as sr
from lib.vocab_retrieval import reset_index_cache, MATCH_MORPHOLOGY_CANDIDATE, MATCH_MORPHOLOGY_EN


def _reset():
    reset_index_cache()


def test_called_cells_not_auto_verified_by_morphology():
    """§H: 'CALLED' must not silently morph into 'Call' without Falcon
    contextual confirmation - with candidate selection disabled, the
    -ed reduction must NOT produce an immediate VERIFIED result."""
    _reset()
    result = sr.resolve_item(
        "CALLED CELLS", source_language="en", source_span="cells, also called the basic unit of life",
        educational_sentence="Cells are called the basic unit of life.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] != sr.STATUS_VERIFIED, f"expected NOT verified without Falcon confirmation, got {result}"
    print("PASS: CALLED CELLS is not auto-verified via morphology alone")


def test_called_cells_rejected_when_falcon_says_none(monkeypatch=None):
    """§H: even WITH candidate selection enabled, if Falcon (correctly)
    declines the false-friend match, verification must not fabricate one."""
    _reset()
    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": None, "reason": "CALLED here means NAMED, not the verb 'to call'", "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "CALLED CELLS", source_language="en", source_span="cells, also called the basic unit of life",
            educational_sentence="Cells are called the basic unit of life.", model="unused",
        )
        assert result["status"] != sr.STATUS_VERIFIED, f"expected rejection, got {result}"
    finally:
        sr._call_falcon_candidate_selection = orig
    print("PASS: CALLED CELLS rejected when Falcon answers NONE in context")


def test_one_brother_essential_information_loss_rejected():
    """§I: a candidate selection that keeps only the quantifier 'One' and
    drops the head noun 'BROTHER' must be rejected outright, even if
    Falcon (incorrectly) selects it."""
    _reset()
    idx = sr.get_index()
    one_row, _ = idx.exact_match("one")
    assert one_row is not None, "test fixture assumption broke: catalog must contain 'One'"

    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": one_row["id"], "reason": "picked One", "confidence": "medium",
    }
    orig_retrieve = idx.retrieve_candidates
    idx.retrieve_candidates = lambda term, top_n=5: [one_row]
    try:
        result = sr.resolve_item(
            "ONE BROTHER", source_language="en", source_span="I have one brother.",
            educational_sentence="I have one brother.", model="unused",
        )
        assert result["status"] != sr.STATUS_VERIFIED, f"expected ESSENTIAL_INFORMATION_LOSS rejection, got {result}"
    finally:
        sr._call_falcon_candidate_selection = orig
        idx.retrieve_candidates = orig_retrieve
    print("PASS: ONE BROTHER -> One rejected as ESSENTIAL_INFORMATION_LOSS")


def test_very_hot_core_with_modifier_loss_accepted_but_flagged():
    """§I/§J: 'VERY HOT' -> 'Hot' keeps the semantic head and should be
    ACCEPTED but classified as CORE_WITH_MODIFIER_LOSS, not FULL."""
    _reset()
    idx = sr.get_index()
    hot_row, _ = idx.exact_match("hot")
    assert hot_row is not None, "test fixture assumption broke: catalog must contain 'Hot'"

    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": hot_row["id"], "reason": "core concept match", "confidence": "high",
    }
    orig_retrieve = idx.retrieve_candidates
    idx.retrieve_candidates = lambda term, top_n=5: [hot_row]
    try:
        result = sr.resolve_item(
            "VERY HOT", source_language="en", source_span="It is very hot today.",
            educational_sentence="It is very hot today.", model="unused",
        )
        assert result["status"] == sr.STATUS_VERIFIED, f"expected VERIFIED (core kept), got {result}"
        assert result["information_loss"] == sr.LOSS_CORE_WITH_MODIFIER_LOSS, result["information_loss"]
    finally:
        sr._call_falcon_candidate_selection = orig
        idx.retrieve_candidates = orig_retrieve
    print("PASS: VERY HOT -> Hot accepted, classified CORE_WITH_MODIFIER_LOSS")


def test_essential_information_loss_never_counted_as_verified_in_coverage():
    """§J: coverage_report must never fold an ESSENTIAL_INFORMATION_LOSS
    rejection into verified_signs / full_verified_lexical_coverage_pct."""
    _reset()
    idx = sr.get_index()
    one_row, _ = idx.exact_match("one")
    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": one_row["id"], "reason": "picked One", "confidence": "low",
    }
    orig_retrieve = idx.retrieve_candidates
    idx.retrieve_candidates = lambda term, top_n=5: [one_row]
    try:
        unit = {
            "source_span": "I have one brother.", "educational_sentence": "I have one brother.",
            "semantic_sign_plan": ["ONE BROTHER"],
        }
        resolved_unit = sr.resolve_unit(unit, "en", "unused")
        report = sr.coverage_report([resolved_unit])
        assert report["verified_signs"] == 0, report
        assert report["full_verified_lexical_coverage_pct"] == 0.0, report
    finally:
        sr._call_falcon_candidate_selection = orig
        idx.retrieve_candidates = orig_retrieve
    print("PASS: ESSENTIAL_INFORMATION_LOSS never inflates coverage metrics")


def test_falcon_hallucinated_id_rejected():
    """Pre-existing safeguard, re-verified: an id Falcon invents outside
    the supplied candidate set must be rejected regardless of confidence."""
    _reset()
    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": "not-a-real-candidate-id-xyz", "reason": "hallucinated", "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "xylem transport mechanism", source_language="en", source_span="the xylem transport mechanism",
            educational_sentence="The xylem transport mechanism moves water.", model="unused",
        )
        assert result["status"] != sr.STATUS_VERIFIED, result
    finally:
        sr._call_falcon_candidate_selection = orig
    print("PASS: Falcon-hallucinated id outside candidate set rejected")


def test_falcon_none_accepted_correctly():
    """Falcon answering NONE must resolve to a non-verified status (falls
    through to fingerspell/review), never forced into a sign."""
    _reset()
    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": None, "reason": "no legitimate match", "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "photosynthesis rate", source_language="en", source_span="the photosynthesis rate",
            educational_sentence="The photosynthesis rate increases with light.", model="unused",
        )
        assert result["status"] != sr.STATUS_VERIFIED, result
    finally:
        sr._call_falcon_candidate_selection = orig
    print("PASS: Falcon NONE handled correctly (no forced sign)")


def test_safe_plural_morphology_still_auto_verifies():
    """Regression guard: the §H fix must not over-correct - SAFE (plural)
    morphology should still auto-verify without needing Falcon at all."""
    _reset()
    idx = sr.get_index()
    plural_hit = None
    for w, rows in idx.en_exact.items():
        cand = w + "s"
        if cand not in idx.en_exact and len(w) > 3:
            plural_hit = (cand, w)
            break
    assert plural_hit, "no fixture word found to test plural morphology"
    query, expected = plural_hit
    result = sr.resolve_item(
        query, source_language="en", source_span=query, educational_sentence=query, model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] == sr.STATUS_VERIFIED, f"expected safe plural morphology to auto-verify, got {result}"
    assert result["match_method"] == MATCH_MORPHOLOGY_EN, result["match_method"]
    print(f"PASS: safe plural morphology ('{query}' -> '{expected}') still auto-verifies without Falcon")


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} resolver regression tests passed")


if __name__ == "__main__":
    run_all()
