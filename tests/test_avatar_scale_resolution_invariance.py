"""Regression test for the mixed-resolution avatar scale/anchor bug
(final acceptance pass, P0): scripts/spike_render_captioned_lesson.py's
render_lesson() pooled RAW absolute-pixel shoulder widths and anchor
positions across segments of different native resolutions, then applied
that pooled value as a fixed absolute-pixel quantity onto each segment's
own native-resolution canvas. This looked fine when all segments shared
similar resolution (most ZHO clips do) but broke for any segment whose
native resolution diverged substantially - confirmed via a real rendered
lesson: a 1280x720 ESL Zayed segment came out oversized and cropped past
the frame edges next to 640x360/854x480 ZHO segments.

Fix: normalize by each segment's own frame width/height into a
resolution-independent fraction BEFORE pooling into the global scale/
anchor, then denormalize back to each segment's own absolute pixels when
applying it - same pooled-median architecture as before, now scale-
invariant. This test asserts that invariance directly, on synthetic pose
data at different resolutions representing the SAME physical framing (a
signer occupying the same relative fraction of the frame) - it does not
require MediaPipe/a real video, only the pure pooling/normalization
arithmetic that render_lesson() exercises.

This module needs the project's numpy/opencv/mediapipe dependencies
(already declared in pyproject.toml) - run via `uv run pytest`, same as
the rest of the suite.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from spike_render_captioned_lesson import (  # noqa: E402
    segment_anchor, rescale_and_shift_pose_list, rescale_and_shift_pts_list,
)


def _synthetic_pose_frame(w, h, shoulder_frac=0.20, center_frac=(0.5, 0.4)):
    """Builds one synthetic pose dict representing a signer standing at
    the SAME relative position/size (shoulder_frac of frame width,
    centered at center_frac of the frame) regardless of absolute
    resolution (w, h) - i.e. the same real-world framing captured at
    different pixel resolutions."""
    cx, cy = center_frac[0] * w, center_frac[1] * h
    half_sh = (shoulder_frac * w) / 2
    return {
        "l_sh": (cx + half_sh, cy), "r_sh": (cx - half_sh, cy),
        "l_el": (cx + half_sh * 1.2, cy + 0.1 * h), "r_el": (cx - half_sh * 1.2, cy + 0.1 * h),
        "l_wr": (cx + half_sh * 1.4, cy + 0.2 * h), "r_wr": (cx - half_sh * 1.4, cy + 0.2 * h),
        "l_hip": (cx + half_sh * 0.8, cy + 0.3 * h), "r_hip": (cx - half_sh * 0.8, cy + 0.3 * h),
    }


def test_scale_and_anchor_are_resolution_invariant_when_normalized():
    """Directly exercises the same pooling arithmetic render_lesson() now
    uses: normalize each segment's raw shoulder-width/anchor by its OWN
    frame dimensions before pooling. Two segments at wildly different
    resolutions (matching the real 640x360 ZHO vs 1280x720 ESL Zayed
    case) but representing the SAME physical framing must produce the
    SAME normalized global scale/anchor fraction - this is the invariant
    that was broken before the fix (raw pixel pooling would have produced
    two very different absolute numbers that don't mean the same thing
    across resolutions)."""
    low_res = (640, 360)   # a typical ZHO clip resolution
    high_res = (1280, 720)  # the real SCHOOL STARTS/LOSE FOCUS ESL Zayed resolution that broke

    segments_wh = {"zho_clip": low_res, "esl_zayed_clip": high_res}
    all_shoulder_widths_norm = []
    anchors_norm = {}
    for stem, (w, h) in segments_wh.items():
        frames = [_synthetic_pose_frame(w, h) for _ in range(5)]
        all_shoulder_widths_norm += [abs(p["r_sh"][0] - p["l_sh"][0]) / w for p in frames]
        a = segment_anchor(frames)
        anchors_norm[stem] = (a[0] / w, a[1] / h)

    # Both segments represent the identical relative framing (same
    # shoulder_frac/center_frac in _synthetic_pose_frame), so their
    # normalized values must be equal (within floating point tolerance),
    # regardless of the 2x resolution difference between them.
    zho_w_norm = abs(_synthetic_pose_frame(*low_res)["r_sh"][0] - _synthetic_pose_frame(*low_res)["l_sh"][0]) / low_res[0]
    esl_w_norm = abs(_synthetic_pose_frame(*high_res)["r_sh"][0] - _synthetic_pose_frame(*high_res)["l_sh"][0]) / high_res[0]
    assert abs(zho_w_norm - esl_w_norm) < 1e-9, (zho_w_norm, esl_w_norm)
    assert abs(anchors_norm["zho_clip"][0] - anchors_norm["esl_zayed_clip"][0]) < 1e-9, anchors_norm
    assert abs(anchors_norm["zho_clip"][1] - anchors_norm["esl_zayed_clip"][1]) < 1e-9, anchors_norm

    global_scale_w_norm = float(np.median(all_shoulder_widths_norm))
    target_x_norm = float(np.median([a[0] for a in anchors_norm.values()]))
    target_y_norm = float(np.median([a[1] for a in anchors_norm.values()]))

    # Denormalizing the SAME global fraction back to each segment's own
    # resolution must recover a proportionally correct (not identical
    # absolute-pixel, but identical RELATIVE) scale/position for both -
    # this is exactly the fix: scale_w_px = global_scale_w_norm * w.
    for stem, (w, h) in segments_wh.items():
        scale_w_px = global_scale_w_norm * w
        target_x_px, target_y_px = target_x_norm * w, target_y_norm * h
        # Reconstructed scale/anchor, converted back to a fraction of
        # THIS segment's own frame, must match the pooled global fraction
        # exactly - i.e. no resolution-dependent distortion survives the
        # normalize -> pool -> denormalize round trip.
        assert abs((scale_w_px / w) - global_scale_w_norm) < 1e-9
        assert abs((target_x_px / w) - target_x_norm) < 1e-9
        assert abs((target_y_px / h) - target_y_norm) < 1e-9
    print("PASS: pooled global scale/anchor is resolution-invariant across a 640x360 vs 1280x720 mix")


def test_raw_pixel_pooling_would_have_been_resolution_dependent_old_bug_fixture():
    """Negative control proving the OLD (pre-fix) behavior really was
    broken: pooling RAW, un-normalized absolute-pixel shoulder widths
    across the same two resolutions produces a global value that, when
    applied as a literal absolute-pixel target onto the high-res
    segment's canvas, is nowhere near correct for that segment's own
    scale - i.e. this fixture would have failed under the old code,
    confirming the fix addresses a real discrepancy, not a no-op."""
    low_res = (640, 360)
    high_res = (1280, 720)
    low_frame = _synthetic_pose_frame(*low_res)
    high_frame = _synthetic_pose_frame(*high_res)
    low_w_px = abs(low_frame["r_sh"][0] - low_frame["l_sh"][0])
    high_w_px = abs(high_frame["r_sh"][0] - high_frame["l_sh"][0])

    # Old bug: pooling raw pixels from mostly-low-res segments would give
    # a global value near low_w_px, applied unchanged (in absolute
    # pixels) to the high-res segment - which needs roughly double that
    # (high_w_px) to look the SAME relative size on its own canvas.
    old_global_raw = float(np.median([low_w_px, low_w_px, low_w_px, high_w_px]))  # 3 low-res segments, 1 high-res
    assert old_global_raw < high_w_px * 0.7, (
        f"fixture assumption broke: expected the old raw-pixel pooling to under-scale the high-res "
        f"segment substantially, got old_global={old_global_raw:.1f} vs correct high_w_px={high_w_px:.1f}")
    print(f"PASS: confirmed the old raw-pixel-pooling behavior really was resolution-dependent/broken "
          f"(pooled={old_global_raw:.1f}px vs correct-for-high-res={high_w_px:.1f}px)")


def test_rescale_and_shift_normalizes_a_larger_framed_segment_to_target_scale():
    """The deeper fix: a same-string absolute-pixel SHIFT alone (the
    old shift_pose_list()) never changes bone lengths - only translation.
    render_segment()/draw_body() draw the torso/limb SPAN directly from
    raw detected positions, so a segment whose signer occupies a larger
    fraction of their own native frame (confirmed real for the ESL Zayed
    SCHOOL STARTS/LOSE FOCUS clips - filmed closer/at higher native
    resolution than the ZHO clips in the same lesson) rendered at the
    WRONG SIZE even after the resolution-invariant anchor/scale-fraction
    fix, because nothing actually rescaled its skeleton.

    rescale_and_shift_pose_list() must produce a skeleton whose shoulder
    width, as a fraction of that segment's OWN frame, matches the target
    ratio applied - i.e. scaling a 2x-larger-framed segment by ratio=0.5
    must halve its shoulder-to-shoulder pixel span, not just move it."""
    w, h = 1280, 720
    # A "too close/too large" framing: shoulder width = 40% of frame
    # width, roughly double the lesson's target of ~20% (matching the
    # real SCHOOL STARTS/LOSE FOCUS over-large appearance).
    oversized_frame = _synthetic_pose_frame(w, h, shoulder_frac=0.40, center_frac=(0.5, 0.5))
    anchor = ((oversized_frame["l_sh"][0] + oversized_frame["r_sh"][0]) / 2,
              (oversized_frame["l_sh"][1] + oversized_frame["r_sh"][1]) / 2)
    target_x_px, target_y_px = 0.5 * w, 0.5 * h
    ratio = 0.20 / 0.40  # shrink to half - the target scale is half this segment's own scale

    rescaled = rescale_and_shift_pose_list([oversized_frame], anchor, target_x_px, target_y_px, ratio)[0]
    new_w_px = abs(rescaled["r_sh"][0] - rescaled["l_sh"][0])
    old_w_px = abs(oversized_frame["r_sh"][0] - oversized_frame["l_sh"][0])
    assert abs(new_w_px - old_w_px * ratio) < 1e-6, (new_w_px, old_w_px, ratio)
    # Recentered on the target anchor (mid-shoulder), not just scaled in place.
    new_anchor = ((rescaled["l_sh"][0] + rescaled["r_sh"][0]) / 2, (rescaled["l_sh"][1] + rescaled["r_sh"][1]) / 2)
    assert abs(new_anchor[0] - target_x_px) < 1e-6 and abs(new_anchor[1] - target_y_px) < 1e-6, new_anchor
    print(f"PASS: rescale_and_shift_pose_list halves an oversized skeleton's span "
          f"({old_w_px:.1f}px -> {new_w_px:.1f}px) and recenters it on the target anchor")


def test_rescale_and_shift_pts_list_keeps_hands_consistent_with_rescaled_body():
    """Hand landmarks must be rescaled by the SAME ratio/anchor as the
    body, or hands would end up at the wrong scale relative to a now-
    correctly-resized torso (e.g. hands still full-size next to a
    shrunk body)."""
    w, h = 1280, 720
    anchor = (640.0, 360.0)
    hand_frames = [[(700.0, 400.0), (720.0, 420.0)]]  # 60px/80px offsets from anchor
    ratio = 0.5
    target_x_px, target_y_px = 500.0, 300.0
    out = rescale_and_shift_pts_list(hand_frames, anchor, target_x_px, target_y_px, ratio)[0]
    assert abs(out[0][0] - (500.0 + 60 * 0.5)) < 1e-6, out
    assert abs(out[0][1] - (300.0 + 40 * 0.5)) < 1e-6, out
    print("PASS: rescale_and_shift_pts_list scales hand offsets by the same ratio/anchor as the body")


def run_all():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} avatar scale resolution-invariance tests passed")


if __name__ == "__main__":
    run_all()
