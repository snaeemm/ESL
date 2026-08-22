#!/usr/bin/env python3
"""
SIDE EXPERIMENT, take 2. Auto-detects pivot points from the alpha shape of
each extracted part instead of eyeballing offsets: for a piece cropped
tightly at both joints (per the asset spec - "each arm piece ends exactly
at the joint"), the proximal pivot is the centroid of its topmost content
rows and the distal pivot is the centroid of its bottommost content rows.
Then attaches child pieces by translating (not yet rotating - this test
keeps each piece's own drawn angle) so pivot points land exactly on their
parent's attachment point. This is what actually fixes the shoulder/elbow
gap from the first composite test.
"""
from PIL import Image
import numpy as np
import os

PARTS = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts"
OUT = "/Users/shaz/MOI-Arabic-Sign-Language/data/zho/spike_mediapipe/avatar_parts/composite_v2.png"
CANVAS = (800, 900)
BG = (240, 246, 250, 255)
BAND = 6  # rows to average over for each pivot estimate


def load(name):
    return Image.open(os.path.join(PARTS, f"{name}.png")).convert("RGBA")


def find_pivots(piece):
    """Returns (proximal_xy, distal_xy) in the piece's own local coords."""
    alpha = np.array(piece.split()[3])
    rows_with_content = np.where((alpha > 10).any(axis=1))[0]
    top_rows = rows_with_content[:BAND]
    bot_rows = rows_with_content[-BAND:]

    def row_centroid(rows):
        xs = []
        for y in rows:
            cols = np.where(alpha[y] > 10)[0]
            if len(cols):
                xs.append(cols.mean())
        x = float(np.mean(xs)) if xs else piece.width / 2
        y = float(np.mean(rows))
        return (x, y)

    return row_centroid(top_rows), row_centroid(bot_rows)


def attach(canvas, piece, proximal_local, target_xy):
    """Pastes piece so its proximal pivot lands exactly at target_xy
    (in canvas coordinates), with no rotation applied (yet)."""
    dest = (int(round(target_xy[0] - proximal_local[0])),
            int(round(target_xy[1] - proximal_local[1])))
    canvas.alpha_composite(piece, dest=dest)
    return dest


def to_canvas(local_xy, dest):
    return (dest[0] + local_xy[0], dest[1] + local_xy[1])


def main():
    canvas = Image.new("RGBA", CANVAS, BG)

    torso = load("torso_kandura")
    torso_alpha = np.array(torso.split()[3])
    # shoulder points: look at a band ~12% down from the top of the torso
    # (past the neckline curve, at the shoulder width) and take the
    # leftmost/rightmost content pixels there
    band_y = int(torso.height * 0.12)
    cols = np.where(torso_alpha[band_y] > 10)[0]
    l_shoulder_local = (float(cols.min()), float(band_y))
    r_shoulder_local = (float(cols.max()), float(band_y))

    torso_dest = (CANVAS[0] // 2 - torso.width // 2, 280)
    canvas.alpha_composite(torso, dest=torso_dest)
    l_shoulder = to_canvas(l_shoulder_local, torso_dest)
    r_shoulder = to_canvas(r_shoulder_local, torso_dest)

    head = load("head_face")
    head_dest = (CANVAS[0] // 2 - head.width // 2, torso_dest[1] - head.height + 45)
    canvas.alpha_composite(head, dest=head_dest)

    def build_arm(prefix, shoulder_xy, hand_name):
        upper = load(f"{prefix}_upper_arm")
        u_prox, u_dist = find_pivots(upper)
        u_dest = attach(canvas, upper, u_prox, shoulder_xy)
        elbow = to_canvas(u_dist, u_dest)

        fore = load(f"{prefix}_forearm")
        f_prox, f_dist = find_pivots(fore)
        f_dest = attach(canvas, fore, f_prox, elbow)
        wrist = to_canvas(f_dist, f_dest)

        hand = load(hand_name)
        h_prox, _ = find_pivots(hand)
        attach(canvas, hand, h_prox, wrist)

        print(f"{prefix}: shoulder={shoulder_xy} elbow={elbow} wrist={wrist}")

    build_arm("left", l_shoulder, "left_open_palm")
    build_arm("right", r_shoulder, "right_thumbs_up")

    canvas.convert("RGB").save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
