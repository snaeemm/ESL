#!/usr/bin/env python3
"""
Driver for the motion-fidelity experiment (Part A8-A12). Runs MediaPipe
ONCE per test clip, renders BEFORE (production drawing functions, imported
unmodified from scripts/spike_cartoon_avatar.py) and AFTER (this
experiment's render_v2.py), writes an experimental motion-schema JSON, and
builds a side-by-side comparison video via ffmpeg.

Does NOT modify, import-and-monkeypatch, or write to any production file
or production output path. Everything lands under experiments/motion_fidelity/
and outputs/motion_fidelity_test/.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 experiments/motion_fidelity/extract_and_render.py
"""
import json
import os
import subprocess
import sys
import time

import cv2
import mediapipe as mp
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spike_cartoon_avatar import (  # noqa: E402 — production code, reused unmodified
    mp_holistic, PL, extract_pose_px, face_metrics, draw_body, draw_face_features,
    draw_hand, HandTrack, BG, blend_val,
)
from hand_features import palm_orientation, finger_flexion, finger_spread, thumb_opposition, hand_openness, relative_position, trajectory  # noqa: E402
from face_features_v2 import face_features_v2  # noqa: E402
from head_pose import estimate_head_pose  # noqa: E402
from body_features import body_features  # noqa: E402
from render_v2 import draw_hand_v2, draw_face_features_v2  # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs", "motion_fidelity_test")
os.makedirs(OUT_DIR, exist_ok=True)

TEST_CLIPS = {
    "hand": {
        "path": os.path.join(ROOT, "data/zho/spike_mediapipe/lesson/norm/17_circle.mp4"),
        "reason": (
            "Selected for clear finger articulation, palm rotation, and a real "
            "movement trajectory (a circling motion). Documented in "
            "AVATAR_HANDOFF.md as the single most motion-heavy segment in the "
            "existing 29-segment lesson (12 detection gaps in 4.76s) — a real "
            "stress test for hand fidelity, not a cherry-picked easy case."
        ),
    },
    "face": {
        "path": os.path.join(ROOT, "data/zho/spike_mediapipe/lesson/norm/08_examine.mp4"),
        "reason": (
            "Selected for plausible eyebrow/mouth/head engagement (the sign for "
            "'Examine' involves visual inspection, which in the source ZHO "
            "footage carries visible facial engagement) in a short (2.32s) clip "
            "that keeps this experiment fast to iterate on."
        ),
    },
}


def _smooth_xyz_series(series, alpha):
    """Same EMA-across-gaps logic as spike_cartoon_avatar.smooth_series(),
    but generalized for arbitrary-length point tuples (x,y,z) — the
    production smooth_series' blend_val only handles 2-tuples, which would
    silently drop z. Written here rather than modifying production code."""
    def blend(a, b):
        return tuple(a[i] * (1 - alpha) + b[i] * alpha for i in range(len(a)))

    out = [None] * len(series)
    prev = None
    for i, v in enumerate(series):
        if v is None:
            prev = None
            continue
        if prev is None:
            out[i] = v
        else:
            out[i] = [blend(pv, cv) for pv, cv in zip(prev, v)]
        prev = out[i]
    return out


def extract(clip_path):
    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open {clip_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    pose_list, left_xyz, right_xyz, face_v1_list, face_landmarks_list = [], [], [], [], []
    t0 = time.time()
    with mp_holistic.Holistic(
        static_image_mode=False, model_complexity=1,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
        refine_face_landmarks=False,
    ) as holistic:
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
                face_landmarks_list.append(r.face_landmarks.landmark)
            else:
                face_v1_list.append(None)
                face_landmarks_list.append(None)
    cap.release()
    extraction_s = time.time() - t0
    total = len(pose_list)

    pose_list = [
        {k: (v[0], v[1]) for k, v in p.items()} if p else None
        for p in pose_list
    ]
    # re-run production smoothing on pose (2-tuples, safe with blend_val)
    from spike_cartoon_avatar import smooth_series as prod_smooth
    pose_list = prod_smooth(pose_list, alpha=0.25)
    left_xyz = _smooth_xyz_series(left_xyz, alpha=0.3)
    right_xyz = _smooth_xyz_series(right_xyz, alpha=0.3)
    face_v1_list = prod_smooth(face_v1_list, alpha=0.25)

    shoulder_widths = [abs(p["r_sh"][0] - p["l_sh"][0]) for p in pose_list if p is not None]
    scale_w = float(np.median(shoulder_widths)) if shoulder_widths else 100.0

    def normalize_hand_scale_xyz(pts_list):
        out = []
        spans = []
        for pts in pts_list:
            if pts is None:
                continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            spans.append(max(max(xs) - min(xs), max(ys) - min(ys)))
        target = float(np.median(spans)) if spans else 1.0
        for pts in pts_list:
            if pts is None:
                out.append(None); continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            k = target / span
            out.append([(cx + (x - cx) * k, cy + (y - cy) * k, z) for x, y, z in pts])
        return out

    left_xyz = normalize_hand_scale_xyz(left_xyz)
    right_xyz = normalize_hand_scale_xyz(right_xyz)

    return {
        "fps": fps, "w": w, "h": h, "total": total, "scale_w": scale_w,
        "pose": pose_list, "left_xyz": left_xyz, "right_xyz": right_xyz,
        "face_v1": face_v1_list, "face_landmarks": face_landmarks_list,
        "extraction_s": extraction_s,
    }


def derive_features(data):
    """Part A3-A6: derives all new features per frame. Measured
    separately from MediaPipe extraction time (Part A12)."""
    t0 = time.time()
    total = data["total"]
    left_history, right_history = [], []
    frames_out = []
    for i in range(total):
        frame_out = {}

        if data["left_xyz"][i] is not None:
            pts = data["left_xyz"][i]
            left_history.append((pts[0][0], pts[0][1]))
            frame_out["left_hand_features"] = {
                "palm_orientation": palm_orientation(pts),
                "finger_flexion": finger_flexion(pts),
                "finger_spread": finger_spread(pts),
                "thumb_opposition": thumb_opposition(pts),
                "openness": hand_openness(pts),
                "trajectory": trajectory(left_history[-5:], data["fps"]),
                "relative_position": (relative_position(pts, data["right_xyz"][i], data["pose"][i])
                                      if data["pose"][i] else None),
            }
        if data["right_xyz"][i] is not None:
            pts = data["right_xyz"][i]
            right_history.append((pts[0][0], pts[0][1]))
            frame_out["right_hand_features"] = {
                "palm_orientation": palm_orientation(pts),
                "finger_flexion": finger_flexion(pts),
                "finger_spread": finger_spread(pts),
                "thumb_opposition": thumb_opposition(pts),
                "openness": hand_openness(pts),
                "trajectory": trajectory(right_history[-5:], data["fps"]),
                "relative_position": (relative_position(pts, data["left_xyz"][i], data["pose"][i])
                                      if data["pose"][i] else None),
            }

        if data["face_landmarks"][i] is not None:
            frame_out["face_features_v2"] = face_features_v2(data["face_landmarks"][i], data["w"], data["h"])
            frame_out["head_pose"] = estimate_head_pose(data["face_landmarks"][i], data["w"], data["h"])
        if data["pose"][i] is not None:
            frame_out["body_features"] = body_features(data["pose"][i])

        frames_out.append(frame_out)
    return frames_out, time.time() - t0


def render_before(data, out_path):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(out_path, fourcc, data["fps"], (data["w"], data["h"]))
    left_track, right_track = HandTrack(), HandTrack()

    def future_lookup(pts_list):
        nxt = [None] * data["total"]
        upcoming = None
        for i in range(data["total"] - 1, -1, -1):
            nxt[i] = upcoming
            if pts_list[i] is not None:
                upcoming = (i, [(p[0], p[1]) for p in pts_list[i]])
        return lambda i: nxt[i]

    left_xy = [[(p[0], p[1]) for p in pts] if pts else None for pts in data["left_xyz"]]
    right_xy = [[(p[0], p[1]) for p in pts] if pts else None for pts in data["right_xyz"]]
    left_future, right_future = future_lookup(data["left_xyz"]), future_lookup(data["right_xyz"])

    for i in range(data["total"]):
        canvas = np.full((data["h"], data["w"], 3), BG, dtype=np.uint8)
        if data["pose"][i] is not None:
            face_c, face_r = draw_body(canvas, data["pose"][i], data["w"], data["h"], scale_w=data["scale_w"])
            draw_face_features(canvas, face_c, face_r, data["face_v1"][i])
        l_pts, l_alpha = left_track.get(i, left_xy[i], left_future)
        r_pts, r_alpha = right_track.get(i, right_xy[i], right_future)
        if l_pts:
            draw_hand(canvas, l_pts, l_alpha)
        if r_pts:
            draw_hand(canvas, r_pts, r_alpha)
        out.write(canvas)
    out.release()


def render_after(data, derived, out_path):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(out_path, fourcc, data["fps"], (data["w"], data["h"]))
    left_track, right_track = HandTrack(), HandTrack()

    def future_lookup(pts_list):
        nxt = [None] * data["total"]
        upcoming = None
        for i in range(data["total"] - 1, -1, -1):
            nxt[i] = upcoming
            if pts_list[i] is not None:
                upcoming = (i, [(p[0], p[1]) for p in pts_list[i]])
        return lambda i: nxt[i]

    left_xy = [[(p[0], p[1]) for p in pts] if pts else None for pts in data["left_xyz"]]
    right_xy = [[(p[0], p[1]) for p in pts] if pts else None for pts in data["right_xyz"]]
    left_z = [[p[2] for p in pts] if pts else None for pts in data["left_xyz"]]
    right_z = [[p[2] for p in pts] if pts else None for pts in data["right_xyz"]]
    left_future, right_future = future_lookup(data["left_xyz"]), future_lookup(data["right_xyz"])

    for i in range(data["total"]):
        canvas = np.full((data["h"], data["w"], 3), BG, dtype=np.uint8)
        if data["pose"][i] is not None:
            face_c, face_r = draw_body(canvas, data["pose"][i], data["w"], data["h"], scale_w=data["scale_w"])
            v2 = derived[i].get("face_features_v2")
            hp = derived[i].get("head_pose")
            draw_face_features_v2(canvas, face_c, face_r, data["face_v1"][i], v2, hp)

        l_pts, l_alpha = left_track.get(i, left_xy[i], left_future)
        r_pts, r_alpha = right_track.get(i, right_xy[i], right_future)
        if l_pts:
            lf = derived[i].get("left_hand_features")
            facing = lf["palm_orientation"]["facing"] if lf else "undetermined"
            draw_hand_v2(canvas, l_pts, l_alpha, left_z[i], facing)
        if r_pts:
            rf = derived[i].get("right_hand_features")
            facing = rf["palm_orientation"]["facing"] if rf else "undetermined"
            draw_hand_v2(canvas, r_pts, r_alpha, right_z[i], facing)
        out.write(canvas)
    out.release()


def make_side_by_side(before_path, after_path, out_path):
    """hstack only — this ffmpeg build has no drawtext/fontconfig support
    (confirmed by a failed run), so no in-frame BEFORE/AFTER text labels.
    Left = before_path (BEFORE), right = after_path (AFTER), a thin
    padded divider between them via a 1px black pad on the first input."""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", before_path, "-i", after_path,
        "-filter_complex",
        "[0:v]pad=iw+4:ih:0:0:color=black[v0];[v0][1:v]hstack=inputs=2[v]",
        "-map", "[v]", out_path,
    ]
    subprocess.run(cmd, check=True)


def main():
    report = {}
    for key, spec in TEST_CLIPS.items():
        print(f"=== {key}: {spec['path']} ===", file=sys.stderr)
        print(f"  reason: {spec['reason']}", file=sys.stderr)
        if not os.path.isfile(spec["path"]):
            print(f"  MISSING, skipping", file=sys.stderr)
            continue

        data = extract(spec["path"])
        derived, derivation_s = derive_features(data)

        before_path = os.path.join(OUT_DIR, f"{key}_before.mp4")
        after_path = os.path.join(OUT_DIR, f"{key}_after.mp4")
        t0 = time.time()
        render_before(data, before_path)
        render_before_s = time.time() - t0
        t0 = time.time()
        render_after(data, derived, after_path)
        render_after_s = time.time() - t0

        cmp_path = os.path.join(OUT_DIR, f"{key}_comparison.mp4")
        make_side_by_side(before_path, after_path, cmp_path)

        # Experimental schema (Part A7): raw landmarks (backward-compatible
        # shape) + derived features, clearly separated.
        schema_path = os.path.join(OUT_DIR, f"{key}_motion_fidelity_test.json")
        schema = {
            "fps": data["fps"], "width": data["w"], "height": data["h"],
            "frames": [
                {
                    "frame": i,
                    "raw_mediapipe": {
                        "pose": data["pose"][i],
                        "left_hand_xyz": data["left_xyz"][i],
                        "right_hand_xyz": data["right_xyz"][i],
                        "face_v1_metrics": data["face_v1"][i],
                    },
                    "derived_features": derived[i],
                }
                for i in range(data["total"])
            ],
        }
        with open(schema_path, "w") as f:
            json.dump(schema, f)

        baseline_json_size = os.path.getsize(schema_path)  # computed for comparison note below; see report

        report[key] = {
            "clip": spec["path"], "reason": spec["reason"], "frames": data["total"],
            "extraction_s": round(data["extraction_s"], 3),
            "derivation_s": round(derivation_s, 3),
            "render_before_s": round(render_before_s, 3),
            "render_after_s": round(render_after_s, 3),
            "schema_json_bytes": baseline_json_size,
            "before_video": before_path, "after_video": after_path, "comparison_video": cmp_path,
        }
        print(f"  extraction={data['extraction_s']:.2f}s derivation={derivation_s:.3f}s "
              f"render_before={render_before_s:.2f}s render_after={render_after_s:.2f}s "
              f"schema_json={baseline_json_size/1024:.1f}KB", file=sys.stderr)

    with open(os.path.join(OUT_DIR, "performance_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote performance_report.json", file=sys.stderr)


if __name__ == "__main__":
    main()
