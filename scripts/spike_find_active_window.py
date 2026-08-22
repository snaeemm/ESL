#!/usr/bin/env python3
"""
SIDE EXPERIMENT. Automates what I did manually by eyeballing sampled frames
for alif/inside: run Holistic once, find the first and last frame index
where a hand is detected, add a small buffer, print the trim window in
seconds. Used to scale the "sentence" demo to more clips without manual
frame review each time.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 scripts/spike_find_active_window.py <clip.mp4>
"""
import sys

import cv2
import mediapipe as mp

mp_holistic = mp.solutions.holistic

BUFFER_FRAMES = 6


def main():
    if len(sys.argv) != 2:
        print("usage: spike_find_active_window.py <clip.mp4>", file=sys.stderr)
        sys.exit(1)
    clip = sys.argv[1]
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25

    first_hand, last_hand, total = None, None, 0
    with mp_holistic.Holistic(
        static_image_mode=False, model_complexity=1,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
    ) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            r = holistic.process(rgb)
            rgb.flags.writeable = True
            if r.left_hand_landmarks or r.right_hand_landmarks:
                if first_hand is None:
                    first_hand = total
                last_hand = total
            total += 1
    cap.release()

    if first_hand is None:
        print(f"NO_HAND_DETECTED total_frames={total}", file=sys.stderr)
        sys.exit(2)

    start_f = max(0, first_hand - BUFFER_FRAMES)
    end_f = min(total - 1, last_hand + BUFFER_FRAMES)
    start_s = start_f / fps
    end_s = end_f / fps
    print(f"{start_s:.2f} {end_s:.2f}")
    print(f"clip={clip} total_frames={total} fps={fps:.1f} "
          f"first_hand={first_hand} last_hand={last_hand} "
          f"-> trim [{start_s:.2f}s, {end_s:.2f}s]", file=sys.stderr)


if __name__ == "__main__":
    main()
