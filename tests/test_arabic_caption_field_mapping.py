"""Regression tests for the Arabic-caption tofu defect.

Root cause: lib.pipeline_runner.prepare_clips_for_units()'s _emit_clip()
helper used to default the Arabic caption text to
`r.get("terminology", {}).get("arabic_term") or r["term"]`. The
"terminology" key is only populated on the FALLBACK resolution layers
(translate-then-fingerspell paths in lib/sign_resolver.py) — an exact
bilingual match (the common case for ZHO catalog VERIFIED_SIGN items) never
sets it. So for every plain ZHO match (FAMILY, FATHER, DOCTOR, MOTHER,
TEACHER, SISTER in the real reported lesson) the lookup silently fell back
to r["term"] — the ENGLISH label — which then got fed through
arabic_reshaper + an Arabic-only font in scripts/spike_render_captioned_
lesson.py's draw_caption(), rendering as tofu boxes. Fingerspell segments
happened to render correctly only because their "terminology" key IS set.

Fix: _emit_clip() now requires an explicit `arabic_text` argument that each
call site supplies from the correct verified field for its render_source
(catalog_ref["word_ar"] for ZHO, supplementary_ref["word_ar"] for ESL
Zayed, fingerspell["arabic_word"] for fingerspelling) -- with an
is_arabic_text() guard that refuses non-Arabic-script text and substitutes
an explicit ARABIC_UNAVAILABLE_MARKER rather than ever fabricating or
mis-mapping a caption.

Plain assert-based script (matches this repo's existing test style) - run
directly:

    .venv/bin/python -m tests.test_arabic_caption_field_mapping
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib.pipeline_runner as pr

TMP = tempfile.mkdtemp(prefix="arabic_caption_field_mapping_")


def _fake_source_clip(name):
    path = os.path.join(TMP, name)
    with open(path, "wb") as f:
        f.write(b"FAKECLIP")
    return path


def _unit(unit_id, resolutions):
    return {"unit_id": unit_id, "source_span": "text", "educational_sentence": "text",
            "sign_resolution": resolutions}


# --- A. is_arabic_text() correctly distinguishes Arabic script from Latin --

def test_is_arabic_text_detector():
    assert pr.is_arabic_text("أسرة") is True
    assert pr.is_arabic_text("FAMILY") is False
    assert pr.is_arabic_text("") is False
    assert pr.is_arabic_text(None) is False
    print("PASS: is_arabic_text distinguishes Arabic script from Latin/empty")


# --- B. ZHO exact-match VERIFIED_SIGN (no "terminology" key) still gets ---
# --- its real Arabic caption from catalog_ref.word_ar, not r["term"] ------

def test_zho_exact_match_uses_catalog_word_ar_not_english_term():
    real_prepare = pr.prepare_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip("family.mp4")}
    try:
        resolution = {
            "term": "FAMILY", "status": "VERIFIED_SIGN", "render_source": "ZHO",
            "catalog_ref": {"id": "zho-001", "word_en": "Family", "word_ar": "أسرة",
                             "category": "general", "video_url": "http://example/x.mp4"},
            "supplementary_ref": None,
            # Deliberately NO "terminology" key -- this is the exact shape
            # an exact-bilingual-match resolution has in production (see
            # lib/sign_resolver.py's exact-match branch), which is what
            # triggered the bug.
        }
        units = [_unit("u1", [resolution])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(
            units, motion_dir, model="unused", source_language="en")
        assert len(segments) == 1, segments
        stem, english, arabic = segments[0]
        assert english == "FAMILY", segments
        assert arabic == "أسرة", f"expected verified Arabic 'أسرة', got {arabic!r} (regression: English term leaking into Arabic caption slot)"
        assert seg_trace[0]["caption_arabic_source_ok"] is True
        print("PASS: ZHO exact-match VERIFIED_SIGN uses catalog_ref.word_ar, never the English term")
    finally:
        pr.prepare_clip = real_prepare


# --- C. Missing/corrupt Arabic never fabricated as the English term -------

def test_missing_arabic_shows_explicit_marker_not_english_term():
    real_prepare = pr.prepare_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip("nowordar.mp4")}
    try:
        resolution = {
            "term": "MYSTERY", "status": "VERIFIED_SIGN", "render_source": "ZHO",
            "catalog_ref": {"id": "zho-002", "word_en": "Mystery", "word_ar": None,
                             "category": "general", "video_url": "http://example/y.mp4"},
            "supplementary_ref": None,
        }
        units = [_unit("u1", [resolution])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(
            units, motion_dir, model="unused", source_language="en")
        assert len(segments) == 1, segments
        stem, english, arabic = segments[0]
        assert arabic == pr.ARABIC_UNAVAILABLE_MARKER, (
            f"expected explicit unavailable marker, got {arabic!r} -- must never fabricate/mis-map Arabic")
        assert arabic != "MYSTERY", "must never silently use the English term as the Arabic caption"
        assert seg_trace[0]["caption_arabic_source_ok"] is False
        print("PASS: missing catalog word_ar renders an explicit unavailable marker, not the English term")
    finally:
        pr.prepare_clip = real_prepare


# --- D. SUSPECT_SOURCE_CORRUPTION word_ar is never treated as authoritative

def test_corrupt_word_ar_integrity_not_used_as_caption():
    real_prepare = pr.prepare_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip("corrupt.mp4")}
    try:
        resolution = {
            "term": "SUSPECT", "status": "VERIFIED_SIGN", "render_source": "ZHO",
            "catalog_ref": {"id": "zho-003", "word_en": "Suspect", "word_ar": "باب الأسرة",
                             "word_ar_integrity": "SUSPECT_SOURCE_CORRUPTION",
                             "category": "general", "video_url": "http://example/z.mp4"},
            "supplementary_ref": None,
        }
        units = [_unit("u1", [resolution])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(
            units, motion_dir, model="unused", source_language="en")
        stem, english, arabic = segments[0]
        assert arabic == pr.ARABIC_UNAVAILABLE_MARKER, (
            f"SUSPECT_SOURCE_CORRUPTION word_ar must not become an authoritative caption, got {arabic!r}")
        print("PASS: SUSPECT_SOURCE_CORRUPTION word_ar is not used as an authoritative caption")
    finally:
        pr.prepare_clip = real_prepare


# --- E. Fingerspell path still uses the whole-word arabic_word (unchanged) -

def test_fingerspell_still_uses_arabic_word():
    real_prepare = pr.prepare_clip
    pr.prepare_clip = lambda cref: {"norm_clip_path": _fake_source_clip("letter.mp4")}
    try:
        resolution = {
            "term": "INCLUDE", "status": "FINGERSPELL_CANDIDATE", "render_source": "FINGERSPELL",
            "catalog_ref": None, "supplementary_ref": None,
            "fingerspell": {
                "fully_resolved": True, "arabic_word": "تُشكِّل",
                "catalog_refs": [
                    {"name_ar": "taa", "catalog_row": {"id": "letter-taa", "word_en": "Taa",
                                                          "category": "alphabet", "video_url": "http://example/l.mp4"}},
                ],
            },
        }
        units = [_unit("u1", [resolution])]
        motion_dir = tempfile.mkdtemp(dir=TMP)
        segments, seg_trace, failures, unresolved = pr.prepare_clips_for_units(
            units, motion_dir, model="unused", source_language="en")
        stem, english, arabic = segments[0]
        assert arabic == "تُشكِّل", segments
        print("PASS: fingerspell segments still caption with the verified whole-word arabic_word")
    finally:
        pr.prepare_clip = real_prepare


if __name__ == "__main__":
    test_is_arabic_text_detector()
    test_zho_exact_match_uses_catalog_word_ar_not_english_term()
    test_missing_arabic_shows_explicit_marker_not_english_term()
    test_corrupt_word_ar_integrity_not_used_as_caption()
    test_fingerspell_still_uses_arabic_word()
    print("ALL PASS")
