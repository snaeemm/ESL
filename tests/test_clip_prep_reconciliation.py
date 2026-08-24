"""Regression tests for the ESL Zayed clip-MATERIALIZATION gap fix.

Root cause: lib/pipeline_runner.py's CLIP_PREP loop only recognized two
shapes — VERIFIED_SIGN+catalog_ref (ZHO) and FINGERSPELL_CANDIDATE+fingerspell
— and silently `continue`d past anything else, including a VERIFIED_SIGN
resolved via ESL_ZAYED (catalog_ref=None, supplementary_ref={...}). That
resolution is real (lib/sign_resolver.py's resolve_item() returns status=
VERIFIED_SIGN, render_source=ESL_ZAYED) and validation.json accepted it, but
no clip was ever produced and no error was ever surfaced — the segment just
vanished from the final video.

The fix extracted the CLIP_PREP loop into lib.pipeline_runner.
prepare_clips_for_units(), added an explicit ESL_ZAYED branch that calls
lib.clip_prep.prepare_esl_zayed_clip(), and added a reconciliation invariant:
every authorized decision (VERIFIED_SIGN or FINGERSPELL_CANDIDATE) must end
up in `segments` or in the returned `unresolved_authorized_items` — never
silently dropped. lib.pipeline_runner.run() now raises PipelineBlocked if
`unresolved_authorized_items` is non-empty, refusing to render an incomplete
video.

These tests exercise prepare_clips_for_units() directly (no Ollama/ffmpeg/
network needed) by monkeypatching lib.pipeline_runner.prepare_clip /
prepare_esl_zayed_clip / resolve_terminology / fingerspell.

Plain assert-based script (matches this repo's existing test style, see
tests/test_esl_zayed_supplementary.py) - run directly:

    .venv/bin/python -m tests.test_clip_prep_reconciliation
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib.pipeline_runner as pr
from lib.clip_prep import ClipPrepError

TMP = tempfile.mkdtemp(prefix="clip_prep_reconciliation_")


def _fake_source_clip(name):
    """A real (tiny, content-irrelevant) file standing in for a prepared
    norm clip — prepare_clips_for_units() only shutil.copyfile()s it."""
    path = os.path.join(TMP, name)
    with open(path, "wb") as f:
        f.write(b"FAKECLIP")
    return path


def _zho_resolution(term="Family", catalog_id="zho-001"):
    return {
        "term": term, "status": "VERIFIED_SIGN", "render_source": "ZHO",
        "catalog_ref": {"id": catalog_id, "word_en": term, "category": "general", "video_url": "http://example/x.mp4"},
        "supplementary_ref": None,
        "terminology": {},
    }


def _esl_zayed_resolution(term="Brother", supplementary_id="ESL_ZAYED_0099"):
    return {
        "term": term, "status": "VERIFIED_SIGN", "render_source": "ESL_ZAYED",
        "catalog_ref": None,
        "supplementary_ref": {
            "supplementary_id": supplementary_id, "youtube_video_id": "yt123",
            "source_url": "https://www.youtube.com/watch?v=yt123",
            "segment_start_s": 4.0, "segment_end_s": 6.0,
            "arabic_text": "أخ", "english_meaning": term,
        },
        "terminology": {},
    }


def _fingerspell_resolution(term="Xenon", letters=("taa", "seen")):
    return {
        "term": term, "status": "FINGERSPELL_CANDIDATE", "render_source": "FINGERSPELL",
        "catalog_ref": None, "supplementary_ref": None,
        "fingerspell": {
            "fully_resolved": True,
            "catalog_refs": [
                {"name_ar": letter, "catalog_row": {"id": f"letter-{letter}", "word_en": letter,
                                                       "category": "alphabet", "video_url": "http://example/l.mp4"}}
                for letter in letters
            ],
        },
        "terminology": {},
    }


def _unit(unit_id, resolutions, source_span="text", educational_sentence="text"):
    return {"unit_id": unit_id, "source_span": source_span, "educational_sentence": educational_sentence,
            "sign_resolution": resolutions}


# --- A. Authorized ESL Zayed sign creates a prepared clip -----------------

def test_esl_zayed_authorized_sign_creates_prepared_clip():
    real_prepare_esl = pr.prepare_esl_zayed_clip
    pr.prepare_esl_zayed_clip = lambda supp_ref: {"norm_clip_path": _fake_source_clip("brother.mp4")}
    try:
        units = [_unit("u1", [_esl_zayed_resolution()])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="en")
        assert len(segments) == 1, segments
        assert segments[0][1] == "Brother", segments
        assert not failures, failures
        assert not unresolved, unresolved
        assert os.path.exists(os.path.join(motion_dir, f"{seg_trace[0]['stem']}.mp4"))
        print("PASS: authorized ESL Zayed sign creates a prepared clip")
    finally:
        pr.prepare_esl_zayed_clip = real_prepare_esl


# --- B. ZHO clip preparation remains unchanged -----------------------------

def test_zho_clip_prep_unchanged():
    real_prepare = pr.prepare_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip("family.mp4")}
    try:
        units = [_unit("u1", [_zho_resolution()])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="en")
        assert len(segments) == 1, segments
        assert segments[0][1] == "Family"
        assert not failures and not unresolved
        print("PASS: ZHO clip preparation unchanged")
    finally:
        pr.prepare_clip = real_prepare


# --- C. Fingerspelling remains unchanged -----------------------------------

def test_fingerspell_clip_prep_unchanged():
    real_prepare = pr.prepare_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip(f"{cref['id']}.mp4")}
    try:
        units = [_unit("u1", [_fingerspell_resolution(letters=("taa", "seen", "kaaf"))])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="ar")
        assert len(segments) == 3, segments
        assert [s[0].split("_", 1)[1] for s in segments] == ["taa", "seen", "kaaf"], segments
        assert not failures and not unresolved
        print("PASS: fingerspelling clip preparation unchanged (multi-letter expansion preserved)")
    finally:
        pr.prepare_clip = real_prepare


# --- D. Missing/broken ESL Zayed source asset cannot silently disappear ---

def test_broken_esl_zayed_source_fails_closed_no_fallback_available():
    real_prepare_esl = pr.prepare_esl_zayed_clip
    real_resolve_term = pr.resolve_terminology
    pr.prepare_esl_zayed_clip = lambda supp_ref: (_ for _ in ()).throw(ClipPrepError("yt-dlp: video unavailable"))
    # No usable Arabic terminology -> fingerspell fallback is not available either.
    pr.resolve_terminology = lambda *a, **k: {"translation_status": "FAILED", "arabic_term": None}
    try:
        units = [_unit("u1", [_esl_zayed_resolution(term="Brother")])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="en")
        assert not segments, "a broken ESL Zayed source with no fallback must not produce a fabricated segment"
        assert len(unresolved) == 1, unresolved
        assert unresolved[0]["term"] == "Brother"
        assert unresolved[0]["render_source"] == "ESL_ZAYED"
        assert any(f.get("render_source") == "ESL_ZAYED" for f in failures), failures
        print("PASS: broken ESL Zayed source with no fingerspell fallback surfaces as unresolved_authorized_items, not a silent drop")
    finally:
        pr.prepare_esl_zayed_clip = real_prepare_esl
        pr.resolve_terminology = real_resolve_term


def test_broken_esl_zayed_source_falls_back_to_fingerspell_when_available():
    real_prepare_esl = pr.prepare_esl_zayed_clip
    real_prepare = pr.prepare_clip
    real_resolve_term = pr.resolve_terminology
    real_fingerspell = pr.fingerspell
    pr.prepare_esl_zayed_clip = lambda supp_ref: (_ for _ in ()).throw(ClipPrepError("download failed"))
    pr.resolve_terminology = lambda *a, **k: {"translation_status": "OK", "arabic_term": "أخ"}
    pr.fingerspell = lambda arabic_word: {
        "fully_resolved": True,
        "catalog_refs": [{"name_ar": "alif", "catalog_row": {"id": "letter-alif", "word_en": "alif",
                                                                "category": "alphabet", "video_url": "http://x"}},
                          {"name_ar": "khaa", "catalog_row": {"id": "letter-khaa", "word_en": "khaa",
                                                                "category": "alphabet", "video_url": "http://x"}}],
    }
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip(f"{cref['id']}.mp4")}
    try:
        units = [_unit("u1", [_esl_zayed_resolution(term="Brother")])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="ar")
        assert len(segments) == 2, segments  # two fingerspelled letters, never zero
        assert not unresolved, unresolved
        assert seg_trace[0].get("fallback_from") == "ESL_ZAYED"
        print("PASS: broken ESL Zayed source with an available fingerspell fallback renders the fallback, never silently drops")
    finally:
        pr.prepare_esl_zayed_clip = real_prepare_esl
        pr.prepare_clip = real_prepare
        pr.resolve_terminology = real_resolve_term
        pr.fingerspell = real_fingerspell


# --- E. Mixed ZHO+ESL Zayed+fingerspell episode reconciles ----------------

def test_mixed_episode_reconciles_planned_vs_prepared():
    real_prepare = pr.prepare_clip
    real_prepare_esl = pr.prepare_esl_zayed_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip(f"{cref['id']}.mp4")}
    pr.prepare_esl_zayed_clip = lambda supp_ref: {"norm_clip_path": _fake_source_clip("esl.mp4")}
    try:
        units = [
            _unit("u1", [_zho_resolution("Father", "zho-f"), _zho_resolution("Mother", "zho-m")]),
            _unit("u2", [_esl_zayed_resolution("Brother")]),
            _unit("u3", [_fingerspell_resolution("Include", letters=("taa", "sheen", "kaaf", "laam"))]),
        ]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="en")
        # 2 ZHO whole-word decisions + 1 ESL Zayed whole-word decision + 1
        # fingerspelled decision expanding into 4 letter clips = 3 authorized
        # decisions -> 2 + 1 + 4 = 7 rendered segment files, reconciled
        # explicitly against the number of resolution decisions (not assumed
        # 1:1, since fingerspelling expands).
        num_decisions = sum(len(u["sign_resolution"]) for u in units)
        assert num_decisions == 4
        assert len(segments) == 7, segments
        assert not unresolved, unresolved
        brother_present = any(s[1] == "Brother" for s in segments)
        assert brother_present, "BROTHER (ESL Zayed) must be physically present among prepared segments"
        print("PASS: mixed ZHO+ESL Zayed+fingerspell episode reconciles decisions vs prepared segments (7 clips from 4 decisions)")
    finally:
        pr.prepare_clip = real_prepare
        pr.prepare_esl_zayed_clip = real_prepare_esl


# --- F. DOCTOR/ZHO priority unchanged --------------------------------------

def test_doctor_zho_priority_unchanged_through_clip_prep():
    """DOCTOR must resolve via ZHO (tested at the resolver level in
    tests/test_esl_zayed_supplementary.py); this confirms that once
    resolved, it also takes the ZHO clip-prep branch, not the ESL_ZAYED one,
    end to end through prepare_clips_for_units()."""
    from lib import sign_resolver as sr
    from lib.vocab_retrieval import reset_index_cache, reset_esl_zayed_index_cache
    reset_index_cache()
    reset_esl_zayed_index_cache()
    resolution = sr.resolve_item("Doctor", source_language="en", source_span="My father is a doctor.",
                                  educational_sentence="My father is a doctor.", model="unused",
                                  allow_candidate_selection=False)
    assert resolution["render_source"] == "ZHO"
    real_prepare = pr.prepare_clip
    real_prepare_esl = pr.prepare_esl_zayed_clip
    esl_called = []
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip("doctor.mp4")}
    pr.prepare_esl_zayed_clip = lambda supp_ref: esl_called.append(1) or {"norm_clip_path": _fake_source_clip("x.mp4")}
    try:
        units = [_unit("u1", [resolution])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(units, motion_dir, model="unused", source_language="en")
        assert len(segments) == 1
        assert not esl_called, "DOCTOR must never take the ESL_ZAYED clip-materialization path"
        print("PASS: DOCTOR/ZHO priority preserved through clip preparation (ESL Zayed path never invoked)")
    finally:
        pr.prepare_clip = real_prepare
        pr.prepare_esl_zayed_clip = real_prepare_esl


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
