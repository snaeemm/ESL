#!/usr/bin/env python3
"""
SIDE EXPERIMENT. Extracts individual parts from the Gemini-generated
composite sheet. Unlike the earlier ChatGPT sheet, this one is a JPEG with
a checkerboard pattern baked into the pixels (no real alpha channel), and
the checkerboard's light tone is close to the white kandura's own color -
plain color-threshold keying would eat into the clothing. Flood-filling
from each crop's corners (background, by construction) respects the
outline strokes as boundaries, so it removes the connected checkerboard
without touching the (disconnected, outlined) garment.
"""
import cv2
import numpy as np
from PIL import Image
import os

SRC = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts/gemini_sheet.jpeg"
OUTDIR = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts"

# Rough (x0,y0,x1,y1) windows for the 1408x768 sheet, 5 columns.
COL_W = 1408 / 5
ROW1 = (0, 295)
ROW2 = (460, 730)
REGIONS = {
    "g_head": (0 * COL_W, ROW1[0], 1 * COL_W, ROW1[1]),
    "g_torso": (1 * COL_W, ROW1[0], 2 * COL_W, ROW1[1]),
    "g_upper_arm": (2 * COL_W, ROW1[0], 3 * COL_W, ROW1[1]),
    "g_forearm": (3 * COL_W, ROW1[0], 4 * COL_W, ROW1[1]),
    "g_hand_open": (4 * COL_W, ROW1[0], 5 * COL_W, ROW1[1]),
    "g_hand_fist": (1 * COL_W, ROW2[0], 2 * COL_W, ROW2[1]),
    "g_hand_point": (2 * COL_W, ROW2[0], 3 * COL_W, ROW2[1]),
    "g_hand_thumbsup": (3 * COL_W, ROW2[0], 4 * COL_W, ROW2[1]),
    "g_hand_flat": (4 * COL_W, ROW2[0], 5 * COL_W, ROW2[1]),
}


def remove_bg_floodfill(bgr, tolerance=18):
    h, w = bgr.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    filled = np.zeros((h, w), np.uint8)
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (0, h // 2), (w - 1, h // 2), (w // 2, h - 1)]
    work = bgr.copy()
    for seed in seeds:
        m = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(work, m, seed, (0, 0, 0),
                       loDiff=(tolerance,) * 3, upDiff=(tolerance,) * 3,
                       flags=4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8))
        filled |= m[1:-1, 1:-1]
    return filled  # 255 where background


def extract(name, box):
    img = Image.open(SRC).convert("RGB")
    crop = img.crop(tuple(int(v) for v in box))
    bgr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
    bg_mask = remove_bg_floodfill(bgr)
    alpha = np.where(bg_mask > 0, 0, 255).astype(np.uint8)
    # light cleanup: erode-dilate to remove speckle from checker edges
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    rgba = np.dstack([np.array(crop), alpha])
    piece = Image.fromarray(rgba, "RGBA")
    bbox = piece.split()[3].getbbox()
    if bbox:
        piece = piece.crop(bbox)
    piece.save(os.path.join(OUTDIR, f"{name}.png"))
    print(f"{name}: {piece.size}")


if __name__ == "__main__":
    for name, box in REGIONS.items():
        extract(name, box)
