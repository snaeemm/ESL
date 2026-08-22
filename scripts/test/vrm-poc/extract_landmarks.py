#!/usr/bin/env python3
"""
Extract per-frame MediaPipe Holistic landmarks (pose + both hands) from the
Alif source clip and dump them to JSON for the VRM retargeting test in this
folder (main.js). World landmarks (metric, hip-centered) are used for the
pose so joint angles are computed from real 3D vectors rather than 2D screen
coordinates.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 scripts/test/vrm-poc/extract_landmarks.py
"""
import json
import os

import cv2
import mediapipe as mp

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"
CLIP = os.path.join(ROOT, "data/zho/spike_mediapipe/trimmed/alif_active.mp4")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets/alif_landmarks.json")

mp_holistic = mp.solutions.holistic


def landmark_list(lm, world=False):
    if lm is None:
        return None
    out = []
    for p in lm.landmark:
        entry = {"x": p.x, "y": p.y, "z": p.z, "visibility": getattr(p, "visibility", 1.0)}
        out.append(entry)
    return out


def main():
    cap = cv2.VideoCapture(CLIP)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames = []
    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=2,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:
        idx = 0
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            result = holistic.process(frame_rgb)

            frames.append({
                "frame": idx,
                "t": idx / fps,
                "pose_world": landmark_list(result.pose_world_landmarks),
                "pose": landmark_list(result.pose_landmarks),
                "left_hand": landmark_list(result.left_hand_landmarks),
                "right_hand": landmark_list(result.right_hand_landmarks),
            })
            idx += 1

    cap.release()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({
            "source": CLIP,
            "fps": fps,
            "width": width,
            "height": height,
            "frame_count": len(frames),
            "frames": frames,
        }, f)

    n_pose = sum(1 for fr in frames if fr["pose_world"])
    n_rhand = sum(1 for fr in frames if fr["right_hand"])
    n_lhand = sum(1 for fr in frames if fr["left_hand"])
    print(f"wrote {OUT}")
    print(f"frames={len(frames)} fps={fps} pose_detected={n_pose} right_hand={n_rhand} left_hand={n_lhand}")


if __name__ == "__main__":
    main()
