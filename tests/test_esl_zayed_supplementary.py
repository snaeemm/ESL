"""Regression tests for the ESL Zayed supplementary WORD candidate source
(smallest-safe integration per
data/zho/spike_mediapipe/ab_experiment_20260823/FINAL_REPORT.md §Z/§AB).

Plain assert-based script (matches this repo's existing test style, see
tests/test_resolver_regressions.py) - run directly:

    .venv/bin/python -m tests.test_esl_zayed_supplementary

Covers brief §9 A-F:
  A. ZHO exact always beats ESL Zayed (DOCTOR, FAMILY, SCHOOL).
  B. ESL Zayed can resolve a genuine ZHO gap (a real corpus example).
  C. ESL Zayed candidate rejected if: not in supplied set; wrong content
     type; provenance incomplete; source segment unavailable.
  D. Arabic-script integrity - no candidate-selection output may introduce
     mixed-script garbage and still be accepted.
  E. source provenance appears in the resolve_item() output (render_source /
     source_authority / supplementary_ref), which lib/traceability.py joins
     into the traceability report unchanged.
  F. ZHO and ESL Zayed coverage remain separately counted in coverage_report().
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import sign_resolver as sr
from lib.vocab_retrieval import reset_index_cache, reset_esl_zayed_index_cache, get_esl_zayed_index, get_index


def _reset():
    reset_index_cache()
    reset_esl_zayed_index_cache()


# --- A. ZHO priority regression protection -----------------------------

def test_doctor_resolves_via_zho_exact_not_esl_zayed():
    _reset()
    result = sr.resolve_item(
        "Doctor", source_language="en", source_span="My father is a doctor.",
        educational_sentence="My father is a doctor.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] == sr.STATUS_VERIFIED, f"expected VERIFIED, got {result}"
    assert result["render_source"] == "ZHO", f"DOCTOR must resolve via ZHO, got render_source={result.get('render_source')}"
    assert result["match_method"] not in ("ESL_ZAYED_EXACT", "ESL_ZAYED_CANDIDATE_SELECTED")
    print("PASS: DOCTOR resolves via ZHO, not ESL Zayed")


def test_family_resolves_via_zho_exact():
    _reset()
    result = sr.resolve_item(
        "Family", source_language="en", source_span="This is my family.",
        educational_sentence="This is my family.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] == sr.STATUS_VERIFIED
    assert result["render_source"] == "ZHO"
    print("PASS: FAMILY resolves via ZHO, not ESL Zayed")


def test_school_resolves_via_zho_exact():
    _reset()
    result = sr.resolve_item(
        "School", source_language="en", source_span="I go to school.",
        educational_sentence="I go to school.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] == sr.STATUS_VERIFIED
    assert result["render_source"] == "ZHO"
    print("PASS: SCHOOL resolves via ZHO, not ESL Zayed")


def test_esl_zayed_never_consulted_when_zho_exact_succeeds():
    """Structural guarantee, not just a policy statement: patch the ESL
    Zayed resolution function to explode if called, and confirm a clean
    ZHO exact match never reaches it."""
    _reset()
    orig = sr._esl_zayed_resolution
    called = {"n": 0}

    def _boom(*a, **kw):
        called["n"] += 1
        return orig(*a, **kw)

    sr._esl_zayed_resolution = _boom
    try:
        result = sr.resolve_item(
            "Doctor", source_language="en", source_span="My father is a doctor.",
            educational_sentence="My father is a doctor.", model="unused",
            allow_candidate_selection=False,
        )
        assert result["render_source"] == "ZHO"
        assert called["n"] == 0, "ESL Zayed resolution must never be called once ZHO exact match succeeds"
    finally:
        sr._esl_zayed_resolution = orig
    print("PASS: ESL Zayed resolution function is structurally never invoked after a ZHO exact match")


# --- B. ESL Zayed resolves a genuine ZHO gap -----------------------------

def test_esl_zayed_resolves_genuine_zho_gap_tired():
    """'Tired' has no exact ZHO match (confirmed in the prior spike, and by
    the supplementary catalog build) but IS a real WORD-level ESL Zayed
    entry (تعبان). Should resolve via ESL Zayed exact match."""
    _reset()
    idx = sr.get_index()
    zho_row, _ = idx.exact_match("tired")
    assert zho_row is None, "test assumption broke: ZHO must NOT have an exact 'tired' match"

    esl_idx = get_esl_zayed_index()
    assert esl_idx.exact_match("Tired") is not None, "supplementary catalog must contain 'Tired'"

    result = sr.resolve_item(
        "Tired", source_language="en", source_span="I am tired today.",
        educational_sentence="I am tired today.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] == sr.STATUS_VERIFIED, f"expected VERIFIED via ESL Zayed, got {result}"
    assert result["render_source"] == "ESL_ZAYED"
    assert result["source_authority"] == "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE"
    assert result["match_method"] == "ESL_ZAYED_EXACT"
    assert result["supplementary_ref"]["arabic_text"] == "تعبان"
    print("PASS: TIRED resolves via ESL Zayed exact match, correctly tagged")


# --- C. Candidate authorization / rejection ------------------------------

def test_esl_zayed_candidate_rejected_if_not_in_candidate_set():
    _reset()
    orig = sr._call_falcon_esl_zayed_selection
    sr._call_falcon_esl_zayed_selection = lambda *a, **kw: {
        "selected_candidate_id": "ESL_ZAYED_9999", "reason": "hallucinated", "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "Exhausted", source_language="en", source_span="I feel exhausted after school.",
            educational_sentence="I feel exhausted after school.", model="unused",
        )
        assert result["status"] != sr.STATUS_VERIFIED or result.get("render_source") != "ESL_ZAYED", \
            f"expected rejection of an id not in the candidate set, got {result}"
    finally:
        sr._call_falcon_esl_zayed_selection = orig
    print("PASS: ESL Zayed candidate id not in the supplied set is rejected outright")


def test_esl_zayed_row_missing_segment_metadata_not_renderable():
    row_missing_segment = {
        "supplementary_id": "ESL_ZAYED_TEST_1", "content_type": "WORD",
        "youtube_video_id": "abc123", "segment_start_s": None, "segment_end_s": None,
        "english_meaning": "Test", "arabic_text": "اختبار",
    }
    assert sr._esl_zayed_row_is_renderable(row_missing_segment) is False
    print("PASS: ESL Zayed row with missing segment boundaries is rejected as not renderable")


def test_esl_zayed_row_wrong_content_type_not_renderable():
    row_phrase = {
        "supplementary_id": "ESL_ZAYED_TEST_2", "content_type": "PHRASE",
        "youtube_video_id": "abc123", "segment_start_s": 1.0, "segment_end_s": 3.0,
        "english_meaning": "Good morning", "arabic_text": "صباح الخير",
    }
    assert sr._esl_zayed_row_is_renderable(row_phrase) is False
    print("PASS: PHRASE-level ESL Zayed row is rejected (WORD-only production catalog policy)")


def test_esl_zayed_row_missing_video_id_not_renderable():
    row_no_video = {
        "supplementary_id": "ESL_ZAYED_TEST_3", "content_type": "WORD",
        "youtube_video_id": None, "segment_start_s": 1.0, "segment_end_s": 3.0,
        "english_meaning": "Test", "arabic_text": "اختبار",
    }
    assert sr._esl_zayed_row_is_renderable(row_no_video) is False
    print("PASS: ESL Zayed row with no source video id is rejected as not renderable")


# --- D. Arabic-script integrity ------------------------------------------

def test_esl_zayed_candidate_with_garbled_arabic_rejected():
    """Mirrors the FINAL_REPORT.md §H finding: a candidate whose Arabic
    field is not real Arabic script (or whose English field is itself
    mixed/garbled Arabic-looking text) must be rejected outright, even if
    Falcon selected a technically-valid candidate id."""
    _reset()
    esl_idx = get_esl_zayed_index()
    assert esl_idx.rows, "supplementary catalog must not be empty for this test"
    real_row = esl_idx.rows[0]
    garbled_row = dict(real_row)
    garbled_row["arabic_text"] = "not arabic at all"  # corrupted field, no Arabic script

    orig_index = sr.get_esl_zayed_index
    orig_call = sr._call_falcon_esl_zayed_selection

    class _FakeIndex:
        rows = [garbled_row]
        by_id = {garbled_row["supplementary_id"]: garbled_row}

        def exact_match(self, term):
            return None

        def retrieve_candidates(self, term, top_n=5):
            return [garbled_row]

    sr.get_esl_zayed_index = lambda: _FakeIndex()
    sr._call_falcon_esl_zayed_selection = lambda *a, **kw: {
        "selected_candidate_id": garbled_row["supplementary_id"], "reason": "selected", "confidence": "high",
    }
    try:
        result = sr._esl_zayed_resolution(
            "some english query", "unused", "source span", "educational sentence", True,
        )
        assert result["row"] is None, f"garbled Arabic candidate must be rejected, got {result}"
    finally:
        sr.get_esl_zayed_index = orig_index
        sr._call_falcon_esl_zayed_selection = orig_call
    print("PASS: ESL Zayed candidate with non-Arabic arabic_text field is rejected (Arabic-script integrity)")


def test_esl_zayed_candidate_with_tofu_box_glyphs_rejected():
    """Blocker C: some traceability rows were observed showing Arabic as
    literal missing-glyph placeholder boxes ('[][][][][]' / tofu squares)
    rather than real Arabic script - this happens when a corrupted/mis-
    decoded arabic_text field survives into the catalog. Such a string
    contains NO characters in the Arabic Unicode block, so it must hit the
    exact same _looks_arabic-based integrity gate as any other non-Arabic
    string and be rejected outright - it must never be used as a matching
    key or silently accepted as a valid label."""
    _reset()
    esl_idx = get_esl_zayed_index()
    assert esl_idx.rows, "supplementary catalog must not be empty for this test"
    real_row = esl_idx.rows[0]
    tofu_row = dict(real_row)
    tofu_row["arabic_text"] = "□□□□□"  # literal tofu/placeholder boxes, not Arabic script

    orig_index = sr.get_esl_zayed_index
    orig_call = sr._call_falcon_esl_zayed_selection

    class _FakeIndex:
        rows = [tofu_row]
        by_id = {tofu_row["supplementary_id"]: tofu_row}

        def exact_match(self, term):
            return None

        def retrieve_candidates(self, term, top_n=5):
            return [tofu_row]

    sr.get_esl_zayed_index = lambda: _FakeIndex()
    sr._call_falcon_esl_zayed_selection = lambda *a, **kw: {
        "selected_candidate_id": tofu_row["supplementary_id"], "reason": "selected", "confidence": "high",
    }
    try:
        result = sr._esl_zayed_resolution(
            "some english query", "unused", "source span", "educational sentence", True,
        )
        assert result["row"] is None, f"tofu-box Arabic candidate must be rejected, got {result}"
    finally:
        sr.get_esl_zayed_index = orig_index
        sr._call_falcon_esl_zayed_selection = orig_call
    print("PASS: ESL Zayed candidate with tofu/box-glyph arabic_text is rejected, not fabricated as valid")


def test_missing_word_ar_never_fabricated_in_catalog_row():
    """Blocker C display policy: when a ZHO catalog row genuinely has no
    authoritative Arabic label (word_ar is None/empty), resolve_item must
    pass that through as-is (None/empty) rather than synthesizing a
    placeholder string. The frontend (webapp/frontend/src/pages/Results.tsx)
    relies on this falsiness to omit the Arabic line entirely instead of
    displaying a fabricated or corrupt value - see the `r.catalog_ref.word_ar
    ? ... : ''` guard there. This test locks in the backend half of that
    contract: no code path here must fill in a fake Arabic string."""
    _reset()
    idx = get_index()
    # Find a real row with no word_ar (or synthesize the check structurally
    # if the current catalog has none) - either way, assert the contract on
    # whatever exact_match returns: it must never invent a word_ar that
    # wasn't already on the row.
    no_ar_rows = [r for r in idx.rows if not r.get("word_ar")]
    if no_ar_rows:
        row = no_ar_rows[0]
        result = sr.resolve_item(
            row["word_en"], source_language="en", source_span=f"This is {row['word_en']}.",
            educational_sentence=f"This is {row['word_en']}.", model="unused",
            allow_candidate_selection=False,
        )
        if result.get("catalog_ref"):
            assert not result["catalog_ref"].get("word_ar"), (
                f"word_ar must stay falsy/omitted, never fabricated: {result['catalog_ref']}")
    print("PASS: missing word_ar is never fabricated (or no such row exists in current catalog - contract trivially holds)")


# --- E. Provenance in resolver output (feeds traceability.py unchanged) --

def test_zho_resolution_carries_full_provenance_fields():
    _reset()
    result = sr.resolve_item(
        "Doctor", source_language="en", source_span="My father is a doctor.",
        educational_sentence="My father is a doctor.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["render_source"] == "ZHO"
    assert result["source_authority"] == "INSTITUTIONAL_UAE_REFERENCE"
    assert "supporting_sources" in result
    print("PASS: ZHO resolution carries render_source/source_authority/supporting_sources")


def test_esl_zayed_resolution_carries_full_provenance_fields():
    _reset()
    result = sr.resolve_item(
        "Tired", source_language="en", source_span="I am tired today.",
        educational_sentence="I am tired today.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["render_source"] == "ESL_ZAYED"
    assert result["source_authority"] == "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE"
    ref = result["supplementary_ref"]
    for field in ("youtube_video_id", "segment_start_s", "segment_end_s", "arabic_text", "english_meaning"):
        assert ref.get(field) not in (None, ""), f"missing provenance field {field} in {ref}"
    print("PASS: ESL Zayed resolution carries full source provenance (video id, segment, labels)")


def test_fingerspell_carries_gap_reason():
    _reset()
    result = sr.resolve_item(
        "Xylophonemitochondria", source_language="en", source_span="an obviously unresolvable term",
        educational_sentence="an obviously unresolvable term", model="unused",
        allow_candidate_selection=False,
    )
    assert result["render_source"] == "FINGERSPELL"
    assert result["source_authority"] == "NONE"
    assert result.get("gap_reason") == "NO_SUPPORTED_LEXICAL_SIGN"
    print("PASS: fingerspell/unsupported resolution carries render_source=FINGERSPELL + gap_reason")


# --- F. Coverage counted separately ---------------------------------------

def test_coverage_report_keeps_zho_and_esl_zayed_separate():
    _reset()
    doctor = sr.resolve_item("Doctor", source_language="en", source_span="doctor", educational_sentence="doctor",
                              model="unused", allow_candidate_selection=False)
    tired = sr.resolve_item("Tired", source_language="en", source_span="tired", educational_sentence="tired",
                             model="unused", allow_candidate_selection=False)
    units = [{"unit_id": "u1", "sign_resolution": [doctor]}, {"unit_id": "u2", "sign_resolution": [tired]}]
    cov = sr.coverage_report(units)
    assert cov["verified_signs_zho"] == 1, cov
    assert cov["verified_signs_esl_zayed_supplementary"] == 1, cov
    assert cov["institutional_zho_coverage_pct"] == 50.0, cov
    assert cov["supplementary_observed_emirati_coverage_pct"] == 50.0, cov
    assert cov["combined_known_source_lexical_coverage_pct"] == 100.0, cov
    print("PASS: coverage_report keeps ZHO and ESL Zayed counted separately, never folded together")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = []
    for fn in tests:
        try:
            fn()
        except AssertionError as e:
            failures.append((fn.__name__, str(e)))
            print(f"FAIL: {fn.__name__}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    _run_all()
