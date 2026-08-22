#!/usr/bin/env python3
"""
SIDE EXPERIMENT - not part of the Episode 1 pipeline or the ZHO indexing
deliverable. Feasibility spike only, to answer: can we extract hand/body
keypoints from a ZHO clip locally, cheaply, and render them as a stylized
stick-figure/avatar overlay? Tests the "Phase 2 avatar retargeting" idea
noted in the coverage report.

NOTE ON MEDIAPIPE VERSION: the current pip release (1.0.1) removed the
legacy mp.solutions API in favor of a new Tasks API (HolisticLandmarker).
That new API crashes natively on this machine (native SIGABRT in
TensorsToDetectionsCalculator, "Service is unavailable" - a Metal/GPU
graph-service registration bug), reproduced identically across Python
3.14 and 3.11 and with/without process sandboxing, so it is a mediapipe
1.0.1 regression, not an environment restriction. Pinning the older
mediapipe==0.10.14, which still has mp.solutions.holistic, avoids it
entirely and runs cleanly (confirmed: picks up the real Metal GL context,
"GL version: 2.1 (2.1 Metal - 90.5), renderer: Apple M1 Pro").

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 scripts/spike_mediapipe_avatar.py
"""
import sys
import time

import cv2
import mediapipe as mp
import numpy as np

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"
import os
CLIP = os.environ.get("SPIKE_CLIP", f"{ROOT}/data/zho/clips/Alphabets/alif_eb6b778b.mp4")
OUT_OVERLAY = os.environ.get("SPIKE_OUT_OVERLAY", f"{ROOT}/data/zho/spike_mediapipe/overlay.mp4")
OUT_AVATAR = os.environ.get("SPIKE_OUT_AVATAR", f"{ROOT}/data/zho/spike_mediapipe/stick_avatar.mp4")

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles


def main():
    cap = cv2.VideoCapture(CLIP)
    if not cap.isOpened():
        print(f"FAILED to open {CLIP}", file=sys.stderr)
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Clip: {w}x{h} @ {fps:.1f}fps, {n_frames} frames", file=sys.stderr)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_overlay = cv2.VideoWriter(OUT_OVERLAY, fourcc, fps, (w, h))
    out_avatar = cv2.VideoWriter(OUT_AVATAR, fourcc, fps, (w, h))

    frames_with_hands = 0
    frames_with_pose = 0
    total = 0
    t0 = time.time()

    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            total += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = holistic.process(rgb)
            rgb.flags.writeable = True

            overlay = frame.copy()
            avatar = np.full((h, w, 3), 30, dtype=np.uint8)  # dark "cartoon" canvas

            if results.pose_landmarks:
                frames_with_pose += 1
                mp_drawing.draw_landmarks(
                    overlay, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style())
                mp_drawing.draw_landmarks(
                    avatar, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style())

            has_hand = bool(results.left_hand_landmarks or results.right_hand_landmarks)
            if has_hand:
                frames_with_hands += 1
            for hand in (results.left_hand_landmarks, results.right_hand_landmarks):
                if hand:
                    mp_drawing.draw_landmarks(
                        overlay, hand, mp_holistic.HAND_CONNECTIONS,
                        landmark_drawing_spec=mp_styles.get_default_hand_landmarks_style())
                    mp_drawing.draw_landmarks(
                        avatar, hand, mp_holistic.HAND_CONNECTIONS,
                        landmark_drawing_spec=mp_styles.get_default_hand_landmarks_style())

            out_overlay.write(overlay)
            out_avatar.write(avatar)

    elapsed = time.time() - t0
    cap.release()
    out_overlay.release()
    out_avatar.release()

    print(f"Processed {total} frames in {elapsed:.1f}s ({total/elapsed:.1f} fps)", file=sys.stderr)
    print(f"Frames with pose detected: {frames_with_pose}/{total} "
          f"({100*frames_with_pose/max(total,1):.0f}%)", file=sys.stderr)
    print(f"Frames with >=1 hand detected: {frames_with_hands}/{total} "
          f"({100*frames_with_hands/max(total,1):.0f}%)", file=sys.stderr)
    print(f"Wrote {OUT_OVERLAY}", file=sys.stderr)
    print(f"Wrote {OUT_AVATAR}", file=sys.stderr)


if __name__ == "__main__":
    main()
