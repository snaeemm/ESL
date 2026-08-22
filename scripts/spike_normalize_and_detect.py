#!/usr/bin/env python3
"""
SIDE EXPERIMENT (continuation of spike_mediapipe_avatar.py). Tests whether
cropping tight to the signer (removing excess background so hands take up
more of the frame) improves MediaPipe hand-detection consistency, which
was the weak point found in the first pass (16-24% of frames).

Two-pass:
  1. Run Holistic once over the raw clip to find the union bounding box of
     every landmark (pose + both hands) ever detected, in pixel space.
  2. ffmpeg-crop to that box (+ margin), upscale, re-run Holistic on the
     normalized clip, and report the before/after hand-detection rate.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 scripts/spike_normalize_and_detect.py
"""
import os
import subprocess
import sys
import time

import cv2
import mediapipe as mp
import numpy as np

mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"
CLIP = os.environ.get("SPIKE_CLIP", f"{ROOT}/data/zho/clips/Alphabets/alif_eb6b778b.mp4")
NAME = os.environ.get("SPIKE_NAME", "alif")
OUTDIR = f"{ROOT}/data/zho/spike_mediapipe/normalized"
os.makedirs(OUTDIR, exist_ok=True)

NORMALIZED_CLIP = f"{OUTDIR}/{NAME}_normalized.mp4"
POSE_OVERLAY = f"{OUTDIR}/{NAME}_pose_overlay.mp4"


def run_holistic(video_path, collect_bbox=False, draw_overlay_to=None):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = None
    if draw_overlay_to:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(draw_overlay_to, fourcc, fps, (w, h))

    min_x, min_y, max_x, max_y = w, h, 0, 0
    total = 0
    frames_with_pose = 0
    frames_with_hands = 0

    with mp_holistic.Holistic(
        static_image_mode=False, model_complexity=1,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
    ) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            total += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            r = holistic.process(rgb)
            rgb.flags.writeable = True

            all_landmark_sets = []
            if r.pose_landmarks:
                frames_with_pose += 1
                all_landmark_sets.append(r.pose_landmarks.landmark)
            has_hand = bool(r.left_hand_landmarks or r.right_hand_landmarks)
            if has_hand:
                frames_with_hands += 1
            if r.left_hand_landmarks:
                all_landmark_sets.append(r.left_hand_landmarks.landmark)
            if r.right_hand_landmarks:
                all_landmark_sets.append(r.right_hand_landmarks.landmark)

            if collect_bbox:
                for lms in all_landmark_sets:
                    for lm in lms:
                        if lm.visibility if hasattr(lm, "visibility") else True:
                            x, y = lm.x * w, lm.y * h
                            min_x, min_y = min(min_x, x), min(min_y, y)
                            max_x, max_y = max(max_x, x), max(max_y, y)

            if writer:
                overlay = frame.copy()
                if r.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        overlay, r.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_styles.get_default_pose_landmarks_style())
                for hand in (r.left_hand_landmarks, r.right_hand_landmarks):
                    if hand:
                        mp_drawing.draw_landmarks(
                            overlay, hand, mp_holistic.HAND_CONNECTIONS,
                            landmark_drawing_spec=mp_styles.get_default_hand_landmarks_style())
                writer.write(overlay)

    cap.release()
    if writer:
        writer.release()

    bbox = (min_x, min_y, max_x, max_y) if collect_bbox and max_x > min_x else None
    return {
        "w": w, "h": h, "total": total,
        "frames_with_pose": frames_with_pose,
        "frames_with_hands": frames_with_hands,
        "bbox": bbox,
    }


def main():
    print(f"=== Pass 1: raw clip, collecting bbox === ({CLIP})", file=sys.stderr)
    t0 = time.time()
    stats1 = run_holistic(CLIP, collect_bbox=True)
    print(f"  {stats1['total']} frames, pose {stats1['frames_with_pose']}/{stats1['total']}, "
          f"hands {stats1['frames_with_hands']}/{stats1['total']} "
          f"({100*stats1['frames_with_hands']/stats1['total']:.0f}%), "
          f"{time.time()-t0:.1f}s", file=sys.stderr)

    if not stats1["bbox"]:
        print("No landmarks detected at all - cannot compute crop box.", file=sys.stderr)
        sys.exit(1)

    min_x, min_y, max_x, max_y = stats1["bbox"]
    w, h = stats1["w"], stats1["h"]
    bw, bh = max_x - min_x, max_y - min_y
    margin_x, margin_y = bw * 0.25, bh * 0.15
    crop_x0 = max(0, min_x - margin_x)
    crop_y0 = max(0, min_y - margin_y)
    crop_x1 = min(w, max_x + margin_x)
    crop_y1 = min(h, max_y + margin_y * 3)  # extra bottom margin - hands drop below pose bbox often
    crop_w = int(crop_x1 - crop_x0)
    crop_h = int(crop_y1 - crop_y0)
    print(f"  bbox=({min_x:.0f},{min_y:.0f},{max_x:.0f},{max_y:.0f}) "
          f"-> crop=({crop_x0:.0f},{crop_y0:.0f},{crop_w},{crop_h})", file=sys.stderr)

    target_h = 720
    scale = target_h / crop_h

    print(f"=== Cropping + upscaling with ffmpeg (scale x{scale:.2f}) ===", file=sys.stderr)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", CLIP,
        "-vf", f"crop={crop_w}:{crop_h}:{int(crop_x0)}:{int(crop_y0)},"
               f"scale=-2:{target_h}:flags=lanczos",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        NORMALIZED_CLIP,
    ], check=True)
    print(f"  Wrote {NORMALIZED_CLIP}", file=sys.stderr)

    print(f"=== Pass 2: normalized clip, re-detecting + drawing overlay ===", file=sys.stderr)
    t0 = time.time()
    stats2 = run_holistic(NORMALIZED_CLIP, draw_overlay_to=POSE_OVERLAY)
    print(f"  {stats2['total']} frames, pose {stats2['frames_with_pose']}/{stats2['total']}, "
          f"hands {stats2['frames_with_hands']}/{stats2['total']} "
          f"({100*stats2['frames_with_hands']/stats2['total']:.0f}%), "
          f"{time.time()-t0:.1f}s", file=sys.stderr)
    print(f"  Wrote {POSE_OVERLAY}", file=sys.stderr)

    print("\n=== SUMMARY ===", file=sys.stderr)
    print(f"Hand detection before: {100*stats1['frames_with_hands']/stats1['total']:.0f}%", file=sys.stderr)
    print(f"Hand detection after:  {100*stats2['frames_with_hands']/stats2['total']:.0f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
