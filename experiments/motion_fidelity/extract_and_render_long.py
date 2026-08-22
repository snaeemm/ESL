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
from face_features_v2 import face_features_v2  # noqa: E402
from head_pose import estimate_head_pose  # noqa: E402
from render_v2 import draw_hand_v3, draw_face_features_v2  # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs", "motion_fidelity_test")
os.makedirs(OUT_DIR, exist_ok=True)
NORM_DIR = os.path.join(ROOT, "data/zho/spike_mediapipe/lesson/norm")

# 9 clips, mixed hand + face motion, ~27s total — a real subset, not the
# full 29-segment/73s lesson. Chosen for variety: talking/mouth motion
# (teacher, explain), face-engagement signs (examine, looking), and
# motion-heavy hand signs (find, circle, center, grows, answer).
CLIP_STEMS = ["03_teacher", "04_explain", "08_examine", "14_looking",
              "16_find", "17_circle", "19_center", "25_grows", "27_answer"]


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
            d["left_xyz"] = smooth_xyz(d["left_xyz"], alpha=0.3)
            d["right_xyz"] = smooth_xyz(d["right_xyz"], alpha=0.3)
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
                        v2 = face_features_v2(d["face_lm"][i], w, h)
                        hp = estimate_head_pose(d["face_lm"][i], w, h)
                        draw_face_features_v2(canvas, face_c, face_r, d["face_v1"][i], v2, hp)
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
