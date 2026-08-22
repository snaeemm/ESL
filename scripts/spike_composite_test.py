#!/usr/bin/env python3
"""
SIDE EXPERIMENT. Proof-of-concept only: composite the extracted avatar
parts (head, torso, arms, one hand pose per side) into a single static
frame using fixed hand-eyeballed offsets - not yet driven by real
keypoint data or proper pivot-point rotation math. This only tests
whether layered-transparent-PNG compositing produces something coherent
before investing in the real per-frame rigging math.
"""
from PIL import Image
import os

PARTS = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts"
OUT = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts/composite_test.png"

CANVAS = (640, 720)
BG = (240, 246, 250, 255)


def load(name):
    return Image.open(os.path.join(PARTS, f"{name}.png")).convert("RGBA")


def paste(canvas, piece, xy):
    canvas.alpha_composite(piece, dest=(int(xy[0]), int(xy[1])))


def main():
    canvas = Image.new("RGBA", CANVAS, BG)

    torso = load("torso_kandura")
    torso_xy = (CANVAS[0] // 2 - torso.width // 2, 260)
    paste(canvas, torso, torso_xy)

    head = load("head_face")
    head_xy = (CANVAS[0] // 2 - head.width // 2, torso_xy[1] - head.height + 40)
    paste(canvas, head, head_xy)

    # left side (viewer's left = character's right arm in the source art,
    # but keeping "left_*" naming consistent with the extracted filenames)
    l_upper = load("left_upper_arm")
    l_upper_xy = (torso_xy[0] - l_upper.width + 55, torso_xy[1] + 20)
    paste(canvas, l_upper, l_upper_xy)

    l_fore = load("left_forearm")
    l_fore_xy = (l_upper_xy[0] - 10, l_upper_xy[1] + l_upper.height - 40)
    paste(canvas, l_fore, l_fore_xy)

    l_hand = load("left_open_palm")
    l_hand_xy = (l_fore_xy[0] - 20, l_fore_xy[1] + l_fore.height - 30)
    paste(canvas, l_hand, l_hand_xy)

    r_upper = load("right_upper_arm")
    r_upper_xy = (torso_xy[0] + torso.width - 55, torso_xy[1] + 20)
    paste(canvas, r_upper, r_upper_xy)

    r_fore = load("right_forearm")
    r_fore_xy = (r_upper_xy[0] + r_upper.width - r_fore.width + 10, r_upper_xy[1] + r_upper.height - 40)
    paste(canvas, r_fore, r_fore_xy)

    r_hand = load("right_thumbs_up")
    r_hand_xy = (r_fore_xy[0] + r_fore.width - r_hand.width + 20, r_fore_xy[1] + r_fore.height - 30)
    paste(canvas, r_hand, r_hand_xy)

    canvas.convert("RGB").save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
