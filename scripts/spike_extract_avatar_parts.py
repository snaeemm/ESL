#!/usr/bin/env python3
"""
SIDE EXPERIMENT. Crops individual rigged-avatar parts out of the single
composite reference sheet the user generated, using the real per-pixel
alpha channel (confirmed present, not just a viewer artifact) to tighten
each rough region down to its actual content bounding box.

Proof-of-concept scope only: extracts head, torso, one arm pair, and a
couple of hand poses, then composites them into one static assembled
frame to test whether the compositing mechanism works at all - not full
per-frame animation yet.
"""
from PIL import Image
import numpy as np
import cv2
import os

SRC = "/Users/shaz/Downloads/ChatGPT Image Aug 17, 2026, 11_11_31 PM.png"
OUTDIR = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts"
os.makedirs(OUTDIR, exist_ok=True)

# Rough (x0, y0, x1, y1) windows eyeballed from the 1536x1024 sheet layout;
# each gets auto-tightened to the real alpha bounding box within it.
REGIONS = {
    "head_face": (390, 20, 660, 400),
    "torso_kandura": (670, 40, 1010, 400),
    "left_upper_arm": (1010, 40, 1140, 400),
    "left_forearm": (1135, 40, 1265, 400),
    "right_upper_arm": (1260, 40, 1395, 400),
    "right_forearm": (1390, 40, 1536, 400),
    "left_open_palm": (130, 470, 295, 630),
    "left_pointing": (465, 470, 640, 630),
    "left_thumbs_up": (635, 470, 795, 630),
    "right_open_palm": (130, 650, 295, 810),
    "right_pointing": (465, 650, 640, 810),
    "right_thumbs_up": (635, 650, 795, 810),
}


def drop_label_strip(piece):
    """Each rough region often grabs the part's text label too (either
    above or below the graphic). Find fully-transparent row gaps within
    the tightened crop and keep only the largest contiguous segment -
    the label is reliably the smaller piece."""
    import numpy as np
    alpha = np.array(piece.split()[3])
    row_has_content = (alpha > 10).any(axis=1)
    segments, start = [], None
    for y, has in enumerate(row_has_content):
        if has and start is None:
            start = y
        elif not has and start is not None:
            segments.append((start, y))
            start = None
    if start is not None:
        segments.append((start, len(row_has_content)))
    if len(segments) <= 1:
        return piece
    best = max(segments, key=lambda s: s[1] - s[0])
    return piece.crop((0, best[0], piece.width, best[1]))


def drop_stray_specks(piece, min_area_ratio=0.03):
    """Keeps only connected alpha components above min_area_ratio of the
    largest component's area - removes small stray marks that leaked in
    from neighboring annotations on the source sheet (e.g. the pivot-point
    diagram's arrow/dot) without needing to know where they are."""
    alpha = np.array(piece.split()[3])
    mask = (alpha > 10).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 2:  # background + at most one component
        return piece
    areas = stats[1:, cv2.CC_STAT_AREA]
    max_area = areas.max()
    keep = np.zeros_like(mask)
    for i, area in enumerate(areas, start=1):
        if area >= max_area * min_area_ratio:
            keep[labels == i] = 1
    arr = np.array(piece)
    arr[:, :, 3] = arr[:, :, 3] * keep
    return Image.fromarray(arr)


def tight_bbox(img, box):
    crop = img.crop(box)
    alpha = crop.split()[3]
    bbox = alpha.getbbox()
    if bbox is None:
        return crop
    piece = crop.crop(bbox)
    piece = drop_stray_specks(piece)
    piece = drop_label_strip(piece)
    # re-tighten horizontally after dropping the label strip
    bbox2 = piece.split()[3].getbbox()
    return piece.crop(bbox2) if bbox2 else piece


def main():
    img = Image.open(SRC).convert("RGBA")
    for name, box in REGIONS.items():
        piece = tight_bbox(img, box)
        out = os.path.join(OUTDIR, f"{name}.png")
        piece.save(out)
        print(f"{name}: {piece.size} -> {out}")


if __name__ == "__main__":
    main()
