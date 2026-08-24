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


def test_temporal_before_not_silently_authorized_as_spatial_amam():
    """Blocker A: English 'BEFORE' used temporally ('before school
    starts') must NOT auto-verify against the catalog's spatial 'Before'
    entry (word_ar='أمام', category='Directions and Locations') via bare
    exact match. With candidate selection disabled (no Falcon available),
    the result must NOT be STATUS_VERIFIED - it must fall through to the
    same contextual-confirmation gate as a risky morphology candidate."""
    _reset()
    idx = sr.get_index()
    before_row, method = idx.exact_match("before")
    assert before_row is not None and method == "EXACT_EN", "fixture assumption broke: catalog must contain exact 'Before'"
    assert before_row.get("category") == "Directions and Locations", before_row
    assert before_row.get("word_ar") == "أمام", before_row

    result = sr.resolve_item(
        "BEFORE", source_language="en", source_span="before school starts",
        educational_sentence="Wash your hands before school starts.", model="unused",
        allow_candidate_selection=False,
    )
    assert result["status"] != sr.STATUS_VERIFIED, (
        f"temporal BEFORE must not silently auto-verify to spatial أمام, got {result}")
    print("PASS: temporal BEFORE is not silently exact-matched to spatial أمام without contextual confirmation")


def test_temporal_before_rejected_when_falcon_says_none_in_context():
    """Blocker A: with Falcon selection enabled, if Falcon (correctly)
    recognizes 'before' here is temporal and declines the spatial
    candidate, verification must not force the spatial sign through."""
    _reset()
    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": None,
        "reason": "'before' here is temporal (before school starts), not the spatial 'in front of' sign",
        "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "BEFORE", source_language="en", source_span="before school starts",
            educational_sentence="Wash your hands before school starts.", model="unused",
        )
        assert result["status"] != sr.STATUS_VERIFIED, result
    finally:
        sr._call_falcon_candidate_selection = orig
    print("PASS: temporal BEFORE rejected when Falcon declines the spatial candidate in context")


def test_spatial_before_still_resolvable_via_falcon_confirmation():
    """Blocker A fix must not over-correct: a genuinely spatial use of
    'before' ('stand before the class') should still be able to resolve
    to the catalog's spatial sign, but only via explicit Falcon
    confirmation, not a silent bare exact match."""
    _reset()
    idx = sr.get_index()
    before_row, _ = idx.exact_match("before")
    orig = sr._call_falcon_candidate_selection
    sr._call_falcon_candidate_selection = lambda *a, **kw: {
        "selected_candidate_id": before_row["id"], "reason": "spatial: standing in front of the class",
        "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "BEFORE", source_language="en", source_span="stand before the class",
            educational_sentence="Stand before the class and read your report.", model="unused",
        )
        assert result["status"] == sr.STATUS_VERIFIED, result
        assert result["catalog_ref"]["id"] == before_row["id"], result
    finally:
        sr._call_falcon_candidate_selection = orig
    print("PASS: genuinely spatial BEFORE still resolvable, but only via explicit Falcon confirmation")


def test_school_starts_single_item_collapse_flagged_not_silent():
    """Blocker B: if the semantic-plan model collapses 'School starts
    early.' into a single item ['SCHOOL'] - silently dropping the
    predicate START - build_sign_plan must NOT report this as a clean
    'OK' plan. It must be flagged (possible_information_loss=True,
    semantic_plan_status=REVIEW_REQUIRED) so resolve_unit's
    review_required propagates and the collapse can never silently
    vanish downstream, while the item(s) actually produced are still
    kept (conservative fallback, not silent deletion)."""
    _reset()
    from lib import sign_plan
    orig = sign_plan._call_ollama_raw
    sign_plan._call_ollama_raw = lambda *a, **kw: '["SCHOOL"]'
    try:
        unit = {"concept": "school routine", "key_terms": ["school", "start"],
                "source_span": "School starts early in the morning.",
                "educational_sentence": "School starts early in the morning."}
        result = sign_plan.build_sign_plan(unit, model="unused")
        assert result["semantic_sign_plan"] == ["SCHOOL"], result
        assert result["semantic_plan_status"] == "REVIEW_REQUIRED", (
            f"single-item collapse of a multi-concept sentence must be flagged, got {result}")
        assert result.get("possible_information_loss") is True, result

        resolved_unit = sr.resolve_unit({**unit, **result}, "en", "unused", allow_candidate_selection=False)
        assert resolved_unit["review_required"] is True, (
            "resolve_unit must propagate the information-loss flag as review_required, not drop it silently")
    finally:
        sign_plan._call_ollama_raw = orig
    print("PASS: 'School starts' single-item collapse is flagged REVIEW_REQUIRED, not silently accepted")


def test_school_starts_two_item_plan_not_flagged():
    """Guard against over-correction: when the plan legitimately captures
    both concepts (['SCHOOL', 'START']), it must NOT be flagged."""
    _reset()
    from lib import sign_plan
    orig = sign_plan._call_ollama_raw
    sign_plan._call_ollama_raw = lambda *a, **kw: '["SCHOOL", "START"]'
    try:
        unit = {"concept": "school routine", "key_terms": ["school", "start"],
                "source_span": "School starts early in the morning.",
                "educational_sentence": "School starts early in the morning."}
        result = sign_plan.build_sign_plan(unit, model="unused")
        assert result["semantic_sign_plan"] == ["SCHOOL", "START"], result
        assert result["semantic_plan_status"] == "OK", result
        assert result.get("possible_information_loss") is False, result
    finally:
        sign_plan._call_ollama_raw = orig
    print("PASS: a genuine two-concept plan is not flagged as information loss")


# --- Arabic->English gloss bridge (corrupted-ZHO-Arabic-label investigation) --

def test_arabic_query_reaches_english_labeled_zho_row_via_gloss_bridge():
    """Investigation finding: ZHO's Mother/Father/Sister rows all share
    the SAME corrupted word_ar value ('باب الأسرة', unrelated to any of
    the three) while their word_en label is correct. Direct Arabic-token
    retrieval can therefore never surface Mother as a candidate for a
    correct Arabic query like 'أمى' ('my mother') - not a normalization
    problem (see test below), a genuine retrieval gap. The gloss bridge
    (lib/terminology.py's gloss_arabic_to_english(), wired into
    lib/sign_resolver.py's _deterministic_lexical_resolution) must let
    such a query still reach the row via its correct ENGLISH label + ZHO
    id, WITHOUT ever fabricating a corrected Arabic label - the catalog's
    word_ar stays untouched, only the retrieval PATH changes."""
    _reset()
    idx = sr.get_index()
    mother_row = None
    for r in idx.rows:
        if r.get("word_en") == "Mother":
            mother_row = r
            break
    assert mother_row is not None, "fixture assumption broke: catalog must contain a 'Mother' row"
    # Confirms (does not fabricate/fix) the corruption claim itself.
    assert mother_row.get("word_ar") not in ("أم", "أمي", "أمى", "والدة"), (
        f"expected Mother's word_ar to be the known-corrupted value, got {mother_row.get('word_ar')!r} - "
        f"if this ever gets fixed upstream this test's premise no longer applies")
    assert idx.exact_match("أمى") == (None, None), "fixture assumption broke: direct Arabic exact match must fail"
    assert idx.clitic_match("أمى") == (None, None, None, None)
    assert idx.retrieve_candidates("أمى") == [], (
        "fixture assumption broke: Arabic-token retrieval must find nothing before the bridge can be tested")

    from lib import terminology
    orig_gloss = terminology.gloss_arabic_to_english
    orig_select = sr._call_falcon_candidate_selection
    terminology.gloss_arabic_to_english = lambda *a, **kw: {"gloss": "Mother", "status": "OK", "reason": "test stub"}
    sr._call_falcon_candidate_selection = lambda item_text, source_span, educational_sentence, candidates, model: {
        "selected_candidate_id": mother_row["id"], "reason": "test stub - matches Mother", "confidence": "high",
    }
    try:
        result = sr.resolve_item(
            "أمى", source_language="ar", source_span="أمى معلمة، وأبي طبيب.",
            educational_sentence="أمى معلمة، وأبي طبيب.", model="unused",
        )
        assert result["status"] == sr.STATUS_VERIFIED, result
        assert result["render_source"] == "ZHO", result
        assert result["catalog_ref"]["id"] == mother_row["id"], result
        # The corrupted Arabic label is never touched/fabricated - it is
        # returned exactly as stored, for the caller/UI to handle per the
        # display policy (never invent a corrected label).
        assert result["catalog_ref"]["word_ar"] == mother_row["word_ar"], result
        assert "gloss bridge" in result["match_reason"], result
    finally:
        terminology.gloss_arabic_to_english = orig_gloss
        sr._call_falcon_candidate_selection = orig_select
    print("PASS: Arabic query with no direct Arabic-token candidates reaches Mother via English gloss bridge + stable ZHO id")


def test_gloss_bridge_never_fires_when_arabic_retrieval_already_found_something():
    """The bridge is a fallback for EMPTY Arabic-side retrieval only -
    must never run (or override) when Arabic-token retrieval already
    found candidates, even a wrong one, so it cannot be used to smuggle
    in an extra candidate alongside a legitimate retrieval result."""
    _reset()
    from lib import terminology
    calls = {"n": 0}
    orig_gloss = terminology.gloss_arabic_to_english

    def _counting_gloss(*a, **kw):
        calls["n"] += 1
        return {"gloss": "Mother", "status": "OK", "reason": "test stub"}
    terminology.gloss_arabic_to_english = _counting_gloss
    try:
        # "أمي" collides at the token-retrieval layer with the real
        # (false-friend) ZHO row word_ar="أمي - غير متعلم" ("Uneducated"),
        # so retrieve_candidates() is non-empty and the bridge must not run.
        idx = sr.get_index()
        assert idx.retrieve_candidates("أمي") != [], (
            "fixture assumption broke: 'أمي' must collide with a real catalog row at the retrieval layer")
        sr.resolve_item(
            "أمي", source_language="ar", source_span="أمي معلمة.",
            educational_sentence="أمي معلمة.", model="unused", allow_candidate_selection=False,
        )
        assert calls["n"] == 0, "gloss bridge must not be called when Arabic-side retrieval already found candidates"
    finally:
        terminology.gloss_arabic_to_english = orig_gloss
    print("PASS: gloss bridge never fires when Arabic-token retrieval already found candidates (even a false friend)")


def test_arabic_modifier_query_via_gloss_bridge_stays_ambiguous_not_falsely_verified():
    """Cross-language safety: an Arabic query WITH a detected modifier
    (e.g. 'أب واحد' = 'one father') that reaches the gloss bridge and
    gets a same-headword English candidate selected must NOT be silently
    treated as a full, safe match - lexical content/modifier overlap is
    structurally impossible to verify across scripts, so this must stay
    AMBIGUOUS and fall through to fingerspelling/review rather than
    risk the exact 'ONE BROTHER'->'One'-class silent information loss
    this whole safeguard exists to prevent, just from the other language
    direction."""
    _reset()
    idx = sr.get_index()
    father_row = None
    for r in idx.rows:
        if r.get("word_en") == "Father" and r.get("category") == "Family":
            father_row = r
            break
    assert father_row is not None, "fixture assumption broke: catalog must contain a 'Father' row"

    # Directly exercises classify_information_loss's cross-language branch
    # (avoids depending on retrieve_candidates() staying empty for this
    # exact query forever - e.g. the catalog's Numbers category already
    # has an Arabic entry for "واحد"/one, which would otherwise make this
    # a retrieval-collision test instead of an information-loss test).
    loss = sr.classify_information_loss("أب واحد", father_row["word_en"])
    assert loss == sr.LOSS_AMBIGUOUS, (
        f"'one father' (has a detected Arabic modifier) selecting plain 'Father' across scripts must stay "
        f"AMBIGUOUS, not be silently trusted as FULL, got {loss}")
    print("PASS: Arabic query with a modifier does not falsely verify via the gloss bridge (stays AMBIGUOUS)")


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} resolver regression tests passed")


if __name__ == "__main__":
    run_all()
