#!/usr/bin/env python3
"""
Longer BEFORE/AFTER comparison (~27s, 9 concatenated cached clips) — the
single short clips in extract_and_render.py made the palm-shading/eyebrow/
blink differences too hard to actually watch and judge. This is NOT a
full-lesson rerender (29 segments, 73s) — a meaningful subset chosen for
varied hand + face motion, per the same "do not rerender the full lesson"
constraint, just long enough to actually evaluate.

Reuses the same production drawing functions (BEFORE) and experimental
render_v2 functions (AFTER) as extract_and_render.py, and the same global-
scale-across-segments technique scripts/spike_render_captioned_lesson.py
already uses for the real lesson (pooled median shoulder width, not
per-clip), so the combined sequence doesn't visibly pulse in size at cuts.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 experiments/motion_fidelity/extract_and_render_long.py
"""
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spike_cartoon_avatar import (  # noqa: E402
    mp_holistic, extract_pose_px, face_metrics, draw_body, draw_face_features,
    draw_hand, HandTrack, BG,
)
from hand_features import palm_orientation  # noqa: E402
from face_features_v2 import (  # noqa: E402
    face_features_v2, compute_brow_calibration, compute_mouth_calibration, compute_mouth_contour_calibration,
    compute_eye_contour_calibration,
)
from head_pose import estimate_head_pose  # noqa: E402
from render_v2 import draw_hand_v3, draw_face_features_v2  # noqa: E402
from one_euro_filter import one_euro_smooth_series  # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs", "motion_fidelity_test")
os.makedirs(OUT_DIR, exist_ok=True)
NORM_DIR = os.path.join(ROOT, "data/zho/spike_mediapipe/lesson/norm")

# 9 clips, mixed hand + face motion, ~27s total — a real subset, not the
# full 29-segment/73s lesson. Chosen for variety: talking/mouth motion
# (teacher, explain), face-engagement signs (examine, looking), and
# motion-heavy hand signs (find, circle, center, grows, answer).
CLIP_STEMS = ["03_teacher", "04_explain", "08_examine", "14_looking",
              "16_find", "17_circle", "19_center", "25_grows", "27_answer"]


def _denoise_hand_series(series, min_run=4, min_surrounding_gap=8):
    """Removes isolated short 'blip' detections — a run of detected
    frames shorter than min_run, surrounded on both sides by gaps of at
    least min_surrounding_gap frames — by nulling them out (treated as
    part of the surrounding gap instead of real detections).

    Confirmed via direct inspection (printing raw per-frame detection
    sequences) that these blips are real and common: e.g. 27_answer's
    left hand shows "........LL.................................................LLL......"
    — a 2-frame and a 3-frame blip, each sandwiched in gaps of 8+ and
    61+ frames. These are almost certainly spurious brief false-positive
    detections (this hand isn't part of these one-handed signs at all),
    not genuine hand use. Left as-is, HandTrack renders the hand flashing
    into existence for 2-3 frames then vanishing again — the reported
    "jittery"/"hand gets lost" artifact. Removing them BEFORE they reach
    HandTrack means a genuinely-unused hand renders as consistently
    absent, not flickering.

    A run that's long enough to plausibly be real hand use (>= min_run)
    is never touched, even if surrounded by long gaps - e.g. 16_find's
    21-frame run is real two-handed motion, not noise, and is preserved.
    """
    n = len(series)
    runs = []  # (start, end_exclusive) of detected runs
    i = 0
    while i < n:
        if series[i] is not None:
            j = i
            while j < n and series[j] is not None:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1

    out = list(series)
    for idx, (start, end) in enumerate(runs):
        run_len = end - start
        if run_len >= min_run:
            continue
        gap_before = start - (runs[idx - 1][1] if idx > 0 else -min_surrounding_gap - 1)
        gap_after = (runs[idx + 1][0] if idx < len(runs) - 1 else n + min_surrounding_gap + 1) - end
        if gap_before >= min_surrounding_gap and gap_after >= min_surrounding_gap:
            for k in range(start, end):
                out[k] = None
    return out


def extract_one(clip_path, holistic):
    cap = cv2.VideoCapture(clip_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    pose_list, left_xyz, right_xyz, face_v1_list, face_lm_list = [], [], [], [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        r = holistic.process(rgb)
        rgb.flags.writeable = True
        pose_list.append(extract_pose_px(r.pose_landmarks.landmark, w, h) if r.pose_landmarks else None)
        left_xyz.append([(lm.x * w, lm.y * h, lm.z) for lm in r.left_hand_landmarks.landmark]
                         if r.left_hand_landmarks else None)
        right_xyz.append([(lm.x * w, lm.y * h, lm.z) for lm in r.right_hand_landmarks.landmark]
                          if r.right_hand_landmarks else None)
        if r.face_landmarks:
            face_v1_list.append(face_metrics(r.face_landmarks.landmark, w, h))
            face_lm_list.append(r.face_landmarks.landmark)
        else:
            face_v1_list.append(None)
            face_lm_list.append(None)
    cap.release()
    return {"fps": fps, "w": w, "h": h, "pose": pose_list, "left_xyz": left_xyz,
            "right_xyz": right_xyz, "face_v1": face_v1_list, "face_lm": face_lm_list}


def _dilate_occlusion(occluded, radius=3):
    """Widen each occluded run by `radius` frames on both sides.

    User-reported: mouth "gitteriness" during the circle sign, at points
    where the hand orbits near the face without ever fully covering it -
    confirmed on 17_circle that the binary occlusion flag flickers
    exactly at the boundary (frames 55-56 sit just under the 0.75x
    threshold as the hand approaches, then a total-detection dropout at
    57, then clearly occluded 58-62). Frames right at that boundary are
    already visibly degraded (mouth "open" and corner values jump before
    the flag ever trips) but get trusted as clean - one becomes the
    held/last-good value frozen across the whole occluded run, and the
    first clean frame after release gets trusted immediately, both
    producing a visible jump. Dilating the mask treats a few frames
    around every occluded run as unsafe too, so hold/calibration always
    draws from a frame that's actually clear of the hand, not just
    technically under threshold."""
    n = len(occluded)
    out = list(occluded)
    for i, o in enumerate(occluded):
        if o:
            for j in range(max(0, i - radius), min(n, i + radius + 1)):
                if occluded[j] is not None:
                    out[j] = True
    return out


def _face_is_occluded(face_lm, left_xyz, right_xyz, w, h):
    """True if any hand landmark is within the face's own bounding
    region — MediaPipe still reports face landmarks as "detected" (not
    None) even when a hand partially covers the face, but those readings
    are visibly noisy (confirmed: user-reported eyebrow spikes happened
    on frames where face detection never actually dropped out). This is
    the actual occlusion signal to gate on, not detection dropout."""
    if face_lm is None:
        return False
    nose = np.array([face_lm[1].x * w, face_lm[1].y * h])
    chin = np.array([face_lm[152].x * w, face_lm[152].y * h])
    face_h = np.linalg.norm(nose - chin) * 2 or 1.0  # rough full-face-height proxy
    for hand in (left_xyz, right_xyz):
        if hand is None:
            continue
        for (x, y, _z) in hand:
            if np.linalg.norm(np.array([x, y]) - nose) < face_h * 0.75:
                return True
    return False


def _blend_v2_value(prev, cur, alpha):
    """Recursively EMA-blends face_features_v2's nested structure: dicts
    blend key-by-key; lists of (x,y) tuples (contour_norm) blend
    elementwise; plain numbers blend directly; strings (eye_state) and
    None (gaze, lip_protrusion) pass through as the CURRENT frame's value
    unchanged — blink/squint/open should stay a real discrete event, not
    get smeared into an intermediate state that never existed."""
    if isinstance(cur, dict):
        return {k: _blend_v2_value(prev.get(k) if isinstance(prev, dict) else None, v, alpha) for k, v in cur.items()}
    if isinstance(cur, list):
        if prev is None or len(prev) != len(cur):
            return cur
        return [_blend_v2_value(pv, cv, alpha) for pv, cv in zip(prev, cur)]
    if isinstance(cur, tuple):
        if prev is None:
            return cur
        return tuple(_blend_v2_value(pv, cv, alpha) for pv, cv in zip(prev, cur))
    if isinstance(cur, (int, float)) and isinstance(prev, (int, float)):
        return prev * (1 - alpha) + cur * alpha
    return cur  # strings, None, or no previous value to blend with


def _smooth_face_v2(series, alpha):
    out, prev = [None] * len(series), None
    for i, v in enumerate(series):
        if v is None:
            prev = None
            continue
        out[i] = v if prev is None else _blend_v2_value(prev, v, alpha)
        prev = out[i]
    return out


def smooth_xyz(series, alpha):
    def blend(a, b):
        return tuple(a[i] * (1 - alpha) + b[i] * alpha for i in range(len(a)))
    out, prev = [None] * len(series), None
    for i, v in enumerate(series):
        if v is None:
            prev = None; continue
        out[i] = v if prev is None else [blend(pv, cv) for pv, cv in zip(prev, v)]
        prev = out[i]
    return out


def main():
    t0 = time.time()
    from spike_cartoon_avatar import smooth_series as prod_smooth

    all_data = []
    with mp_holistic.Holistic(static_image_mode=False, model_complexity=1,
                               min_detection_confidence=0.5, min_tracking_confidence=0.5,
                               refine_face_landmarks=False) as holistic:
        for stem in CLIP_STEMS:
            path = os.path.join(NORM_DIR, f"{stem}.mp4")
            print(f"extracting {stem}...", file=sys.stderr)
            d = extract_one(path, holistic)
            d["pose"] = prod_smooth([{k: (v[0], v[1]) for k, v in p.items()} if p else None for p in d["pose"]], alpha=0.25)
            # Denoise BEFORE smoothing: isolated short blip detections
            # (confirmed real via direct inspection - e.g. 27_answer's
            # left hand briefly "detected" for 2-3 frames in the middle
            # of a 60+ frame gap) must be removed first, or the smoother
            # would treat each blip as a real short detected run and
            # smooth INTO it, which still produces a visible flash.
            d["left_xyz"] = _denoise_hand_series(d["left_xyz"])
            d["right_xyz"] = _denoise_hand_series(d["right_xyz"])
            # One-Euro filter replaces the fixed-alpha EMA (smooth_xyz)
            # for hands specifically - adaptive smoothing (heavier when
            # slow/still, lighter when moving fast) is what real
            # continuous multi-gap motion like the circle sign needs to
            # stop feeling like separately-smoothed segments stitched
            # together, per user feedback comparing directly against the
            # real signer footage.
            d["left_xyz"] = one_euro_smooth_series(d["left_xyz"], d["fps"])
            d["right_xyz"] = one_euro_smooth_series(d["right_xyz"], d["fps"])
            d["face_v1"] = prod_smooth(d["face_v1"], alpha=0.25)
            all_data.append(d)
    extraction_s = time.time() - t0

    w, h, fps = all_data[0]["w"], all_data[0]["h"], all_data[0]["fps"]

    # Pooled global scale across all 9 clips (same technique
    # spike_render_captioned_lesson.py uses across the real lesson's 29
    # segments) so the character doesn't pulse size at each cut.
    all_widths = []
    for d in all_data:
        all_widths += [abs(p["r_sh"][0] - p["l_sh"][0]) for p in d["pose"] if p is not None]
    scale_w = float(np.median(all_widths)) if all_widths else 100.0

    def norm_hand_scale(pts_list):
        spans = []
        for pts in pts_list:
            if pts is None:
                continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            spans.append(max(max(xs) - min(xs), max(ys) - min(ys)))
        target = float(np.median(spans)) if spans else 1.0
        out = []
        for pts in pts_list:
            if pts is None:
                out.append(None); continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            k = target / span
            out.append([(cx + (x - cx) * k, cy + (y - cy) * k, z) for x, y, z in pts])
        return out

    for d in all_data:
        d["left_xyz"] = norm_hand_scale(d["left_xyz"])
        d["right_xyz"] = norm_hand_scale(d["right_xyz"])

    # Precompute face_features_v2 for every frame once (was previously
    # recomputed inline during rendering) so it can ALSO be pooled across
    # all 9 clips into one brow_calibration BEFORE rendering starts —
    # same two-pass pattern as scale_w above (detect everything, THEN
    # render), needed because you can't know a clip's own brow range
    # until you've looked at all its frames.
    all_v2 = []
    for d in all_data:
        raw_v2 = [face_features_v2(lm, w, h) if lm is not None else None for lm in d["face_lm"]]

        # BUG FIX (user-reported: "eyebrows go crazy when face gets
        # covered by hand"): a hand partially covering the face makes
        # MediaPipe's face landmarks noisy WITHOUT dropping detection
        # (face_lm is never None here - confirmed by direct inspection).
        # occluded[i] flags those frames; for calibration we POOL ONLY
        # non-occluded frames (so one noisy occluded frame can't skew the
        # brow/mouth range), and for rendering we HOLD the last known-good
        # (non-occluded) reading instead of trusting the noisy one -
        # same "don't fabricate motion you don't actually know" principle
        # scripts/spike_cartoon_avatar.py's HandTrack already uses for
        # missing hand landmarks, applied here to noisy-not-missing face data.
        occluded = [_face_is_occluded(lm, lx, rx, w, h)
                    for lm, lx, rx in zip(d["face_lm"], d["left_xyz"], d["right_xyz"])]
        occluded = _dilate_occlusion(occluded, radius=3)
        d["face_occluded"] = occluded

        # BUG FIX (user-reported: "one of the eyebrows goes way higher
        # than it should for a moment, likely false detection" during
        # circular hand motion). Root cause confirmed on 17_circle: a
        # single frame of total face-detection dropout (v2 is None, e.g.
        # frame 57) was resetting last_good to None. The very next frame
        # (58) was flagged occluded but, with last_good now None, the
        # hold fell through to the raw noisy reading instead of holding
        # - producing exactly this spike (brow value 0.172 vs a stable
        # ~0.133 baseline on both neighbors). A one-frame total dropout
        # doesn't mean the last known-good reading is stale, so it must
        # not be discarded here.
        held_v2 = []
        last_good = None
        for v2, occ in zip(raw_v2, occluded):
            if v2 is None:
                held_v2.append(None)
                continue
            if occ and last_good is not None:
                held_v2.append(last_good)  # hold, don't trust the noisy reading
            else:
                held_v2.append(v2)
                last_good = v2

        # BUG FIX (user-reported jitter): unlike v1's face_metrics(), which
        # gets EMA-smoothed (prod_smooth, alpha=0.25) before rendering,
        # face_v2 was being computed fresh from RAW unsmoothed landmarks
        # every single frame with no filtering at all - that IS the
        # jitter, not a rendering issue. _smooth_face_v2 applies the same
        # EMA idea recursively over the nested dict/list structure.
        d["face_v2"] = _smooth_face_v2(held_v2, alpha=0.25)

        all_v2.extend(v2 for v2, occ in zip(raw_v2, occluded) if v2 is not None and not occ)
    brow_calibration = compute_brow_calibration(all_v2)
    mouth_calibration = compute_mouth_calibration(all_v2)
    mouth_contour_calibration = compute_mouth_contour_calibration(all_v2)
    eye_contour_calibration = compute_eye_contour_calibration(all_v2)
    print(f"brow_calibration: {brow_calibration}", file=sys.stderr)
    print(f"mouth_calibration: {mouth_calibration}", file=sys.stderr)

    def render(out_path, use_v2):
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        for d in all_data:
            total = len(d["pose"])
            left_track, right_track = HandTrack(), HandTrack()

            def future_lookup(pts_list):
                nxt = [None] * total
                upcoming = None
                for i in range(total - 1, -1, -1):
                    nxt[i] = upcoming
                    if pts_list[i] is not None:
                        upcoming = (i, [(p[0], p[1]) for p in pts_list[i]])
                return lambda i: nxt[i]

            left_xy = [[(p[0], p[1]) for p in pts] if pts else None for pts in d["left_xyz"]]
            right_xy = [[(p[0], p[1]) for p in pts] if pts else None for pts in d["right_xyz"]]
            left_z = [[p[2] for p in pts] if pts else None for pts in d["left_xyz"]]
            right_z = [[p[2] for p in pts] if pts else None for pts in d["right_xyz"]]
            lf, rf = future_lookup(d["left_xyz"]), future_lookup(d["right_xyz"])

            for i in range(total):
                canvas = np.full((h, w, 3), BG, dtype=np.uint8)
                if d["pose"][i] is not None:
                    face_c, face_r = draw_body(canvas, d["pose"][i], w, h, scale_w=scale_w)
                    if use_v2 and d["face_lm"][i] is not None:
                        v2 = d["face_v2"][i]
                        hp = estimate_head_pose(d["face_lm"][i], w, h)
                        draw_face_features_v2(canvas, face_c, face_r, d["face_v1"][i], v2, hp, brow_calibration, mouth_calibration, mouth_contour_calibration, eye_contour_calibration)
                    else:
                        draw_face_features(canvas, face_c, face_r, d["face_v1"][i])

                l_pts, l_alpha = left_track.get(i, left_xy[i], lf)
                r_pts, r_alpha = right_track.get(i, right_xy[i], rf)
                if l_pts:
                    if use_v2:
                        nz = palm_orientation(d["left_xyz"][i], handedness="left")["normal"][2] if d["left_xyz"][i] else None
                        draw_hand_v3(canvas, l_pts, l_alpha, left_z[i], nz)
                    else:
                        draw_hand(canvas, l_pts, l_alpha)
                if r_pts:
                    if use_v2:
                        nz = palm_orientation(d["right_xyz"][i], handedness="right")["normal"][2] if d["right_xyz"][i] else None
                        draw_hand_v3(canvas, r_pts, r_alpha, right_z[i], nz)
                    else:
                        draw_hand(canvas, r_pts, r_alpha)
                writer.write(canvas)
        writer.release()

    before_path = os.path.join(OUT_DIR, "long_before.mp4")
    after_path = os.path.join(OUT_DIR, "long_after.mp4")
    t0 = time.time()
    render(before_path, use_v2=False)
    render_before_s = time.time() - t0
    t0 = time.time()
    render(after_path, use_v2=True)
    render_after_s = time.time() - t0

    cmp_path = os.path.join(OUT_DIR, "long_comparison.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", before_path, "-i", after_path,
        "-filter_complex", "[0:v]pad=iw+4:ih:0:0:color=black[v0];[v0][1:v]hstack=inputs=2[v]",
        "-map", "[v]", cmp_path,
    ], check=True)

    total_frames = sum(len(d["pose"]) for d in all_data)
    print(f"\nclips: {CLIP_STEMS}", file=sys.stderr)
    print(f"total frames: {total_frames} (~{total_frames/fps:.1f}s @ {fps}fps)", file=sys.stderr)
    print(f"extraction: {extraction_s:.2f}s  render_before: {render_before_s:.2f}s  render_after: {render_after_s:.2f}s", file=sys.stderr)
    print(f"before: {before_path}\nafter: {after_path}\ncomparison: {cmp_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
