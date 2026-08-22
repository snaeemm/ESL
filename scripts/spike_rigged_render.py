#!/usr/bin/env python3
"""
SIDE EXPERIMENT, take 3: real per-frame rigged rendering. Rotates the
upper-arm/forearm art pieces around their auto-detected pivots to match
the actual tracked shoulder/elbow/wrist angles from MediaPipe, frame by
frame - the piece missing from the static composite test (which only
proved attachment, not motion).

Simplification stated plainly: hand pose is fixed per run (not yet
classified per frame from the tracked handshape) - that's the next real
piece of work, not attempted here.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with pillow --with numpy python3 scripts/spike_rigged_render.py
"""
import math
import os
import sys

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image

mp_holistic = mp.solutions.holistic
PL = mp_holistic.PoseLandmark

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"
PARTS = f"{ROOT}/data/zho/spike_mediapipe/avatar_parts"
CLIP = os.environ.get("SPIKE_CLIP", f"{ROOT}/data/zho/spike_mediapipe/trimmed/alif_active.mp4")
OUT_FRAMES = f"{ROOT}/data/zho/spike_mediapipe/rigged/frames"
OUT_VIDEO = f"{ROOT}/data/zho/spike_mediapipe/rigged/rigged_test.mp4"
os.makedirs(OUT_FRAMES, exist_ok=True)

CANVAS = (800, 900)
BG = (240, 246, 250, 255)
BAND = 6


def load(name):
    return Image.open(os.path.join(PARTS, f"{name}.png")).convert("RGBA")


def find_pivots(piece):
    alpha = np.array(piece.split()[3])
    rows = np.where((alpha > 10).any(axis=1))[0]
    top_rows, bot_rows = rows[:BAND], rows[-BAND:]

    def centroid(rowset):
        xs = []
        for y in rowset:
            cols = np.where(alpha[y] > 10)[0]
            if len(cols):
                xs.append(cols.mean())
        return (float(np.mean(xs)) if xs else piece.width / 2, float(np.mean(rowset)))

    return centroid(top_rows), centroid(bot_rows)


def natural_angle(prox, dist):
    return math.degrees(math.atan2(dist[1] - prox[1], dist[0] - prox[0]))


def scale_piece(piece, pivot, factor):
    """Uniformly scales the piece around `pivot` (not around its own
    corner) - resize normally distorts around (0,0), so this resizes
    then repositions to keep the pivot fixed in place. Returns the scaled
    image and the pivot's (unchanged) local coordinates."""
    if abs(factor - 1.0) < 0.02:
        return piece, pivot
    factor = max(0.5, min(1.8, factor))  # clamp - art shouldn't stretch wildly
    new_size = (max(1, int(piece.width * factor)), max(1, int(piece.height * factor)))
    resized = piece.resize(new_size, Image.LANCZOS)
    return resized, (pivot[0] * factor, pivot[1] * factor)


def rotate_around(piece, pivot, target_angle_deg, natural_angle_deg):
    """Pads the image so `pivot` sits at the exact center, then rotates
    around that center - the pivot's canvas position after rotation is
    therefore always exactly the new canvas center, with no post-rotation
    coordinate math needed."""
    cx, cy = pivot
    w, h = piece.size
    new_w = int(2 * max(cx, w - cx)) + 2
    new_h = int(2 * max(cy, h - cy)) + 2
    padded = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    px, py = int(new_w / 2 - cx), int(new_h / 2 - cy)
    padded.paste(piece, (px, py), piece)
    delta = target_angle_deg - natural_angle_deg
    rotated = padded.rotate(-delta, resample=Image.BICUBIC, expand=False, center=(new_w / 2, new_h / 2))
    return rotated, (new_w / 2, new_h / 2)


def attach(canvas, piece, local_pivot, target_xy):
    dest = (int(round(target_xy[0] - local_pivot[0])), int(round(target_xy[1] - local_pivot[1])))
    canvas.alpha_composite(piece, dest=dest)


def render_frame(torso, head, torso_dest, l_shoulder, r_shoulder,
                  l_elbow_angle, l_wrist_angle, r_elbow_angle, r_wrist_angle,
                  l_upper_len, l_fore_len, r_upper_len, r_fore_len,
                  l_upper_nat, l_fore_nat, r_upper_nat, r_fore_nat,
                  l_hand_name, r_hand_name):
    canvas = Image.new("RGBA", CANVAS, BG)
    canvas.alpha_composite(torso, dest=torso_dest)
    head_dest = (CANVAS[0] // 2 - head.width // 2, torso_dest[1] - head.height + 45)
    canvas.alpha_composite(head, dest=head_dest)

    def build_arm(prefix, shoulder_xy, upper_angle, fore_angle, target_upper_len, target_fore_len,
                  upper_nat, fore_nat, hand_name):
        upper = load(f"{prefix}_upper_arm")
        u_prox, u_dist = find_pivots(upper)
        natural_upper_len = math.hypot(u_dist[0] - u_prox[0], u_dist[1] - u_prox[1])
        upper_scaled, u_prox_s = scale_piece(upper, u_prox, target_upper_len / max(1.0, natural_upper_len))
        rotated_u, new_pivot_u = rotate_around(upper_scaled, u_prox_s, upper_angle, upper_nat[0])
        attach(canvas, rotated_u, new_pivot_u, shoulder_xy)
        # distal pivot after scale+rotate: target_upper_len along upper_angle direction
        rad = math.radians(upper_angle)
        elbow_xy = (shoulder_xy[0] + target_upper_len * math.cos(rad),
                    shoulder_xy[1] + target_upper_len * math.sin(rad))

        fore = load(f"{prefix}_forearm")
        f_prox, f_dist = find_pivots(fore)
        natural_fore_len = math.hypot(f_dist[0] - f_prox[0], f_dist[1] - f_prox[1])
        fore_scaled, f_prox_s = scale_piece(fore, f_prox, target_fore_len / max(1.0, natural_fore_len))
        rotated_f, new_pivot_f = rotate_around(fore_scaled, f_prox_s, fore_angle, fore_nat[0])
        attach(canvas, rotated_f, new_pivot_f, elbow_xy)
        rad2 = math.radians(fore_angle)
        wrist_xy = (elbow_xy[0] + target_fore_len * math.cos(rad2),
                    elbow_xy[1] + target_fore_len * math.sin(rad2))

        hand = load(hand_name)
        h_prox, _ = find_pivots(hand)
        attach(canvas, hand, h_prox, wrist_xy)

    build_arm("left", l_shoulder, l_elbow_angle, l_wrist_angle, l_upper_len, l_fore_len,
              l_upper_nat, l_fore_nat, l_hand_name)
    build_arm("right", r_shoulder, r_elbow_angle, r_wrist_angle, r_upper_len, r_fore_len,
              r_upper_nat, r_fore_nat, r_hand_name)
    return canvas


def main():
    torso = load("torso_kandura")
    head = load("head_face")
    torso_alpha = np.array(torso.split()[3])
    band_y = int(torso.height * 0.12)
    cols = np.where(torso_alpha[band_y] > 10)[0]
    l_shoulder_local = (float(cols.min()), float(band_y))
    r_shoulder_local = (float(cols.max()), float(band_y))
    torso_dest = (CANVAS[0] // 2 - torso.width // 2, 280)
    l_shoulder = (torso_dest[0] + l_shoulder_local[0], torso_dest[1] + l_shoulder_local[1])
    r_shoulder = (torso_dest[0] + r_shoulder_local[0], torso_dest[1] + r_shoulder_local[1])

    l_upper_nat = find_pivots(load("left_upper_arm"))
    l_fore_nat = find_pivots(load("left_forearm"))
    r_upper_nat = find_pivots(load("right_upper_arm"))
    r_fore_nat = find_pivots(load("right_forearm"))
    l_upper_nat_angle = (natural_angle(*l_upper_nat),)
    l_fore_nat_angle = (natural_angle(*l_fore_nat),)
    r_upper_nat_angle = (natural_angle(*r_upper_nat),)
    r_fore_nat_angle = (natural_angle(*r_fore_nat),)

    cap = cv2.VideoCapture(CLIP)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    pose_list = []
    with mp_holistic.Holistic(static_image_mode=False, model_complexity=1,
                               min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            r = holistic.process(rgb)
            if r.pose_landmarks:
                lm = r.pose_landmarks.landmark

                def P(idx):
                    return (lm[idx].x * w, lm[idx].y * h)
                # NOTE the swap: MediaPipe labels landmarks anatomically
                # (the subject's own left/right). For a normal, unmirrored,
                # forward-facing camera - confirmed empirically: the active
                # hand in the alif clip is MediaPipe's "right_hand", but the
                # signing hand visibly appears on the screen-LEFT side - the
                # subject's anatomical right is the viewer's screen-left.
                # "l_*"/"r_*" below mean screen-left/screen-right (matching
                # the canvas layout), so PL.RIGHT_* feeds l_*, not l_*.
                pose_list.append({
                    "l_sh": P(PL.RIGHT_SHOULDER), "l_el": P(PL.RIGHT_ELBOW), "l_wr": P(PL.RIGHT_WRIST),
                    "r_sh": P(PL.LEFT_SHOULDER), "r_el": P(PL.LEFT_ELBOW), "r_wr": P(PL.LEFT_WRIST),
                })
            else:
                pose_list.append(None)
    cap.release()

    # light smoothing, same idea as the procedural renderer
    def smooth(lst, alpha=0.25):
        out, prev = [None] * len(lst), None
        for i, v in enumerate(lst):
            if v is None:
                prev = None
                continue
            if prev is None:
                out[i] = v
            else:
                out[i] = {k: (prev[k][0] * (1 - alpha) + v[k][0] * alpha,
                              prev[k][1] * (1 - alpha) + v[k][1] * alpha) for k in v}
            prev = out[i]
        return out

    pose_list = smooth(pose_list)

    # Fixed per-clip body scale: converts tracked video-space distances
    # into canvas-space pixel lengths, using the ratio between the art's
    # own (fixed) shoulder width and the median tracked shoulder width -
    # same "fixed scale, not per-frame" principle as the procedural
    # renderer, so bone lengths don't pulse with detection noise.
    art_shoulder_w = abs(r_shoulder[0] - l_shoulder[0])
    tracked_widths = [abs(p["r_sh"][0] - p["l_sh"][0]) for p in pose_list if p]
    median_tracked_w = float(np.median(tracked_widths)) if tracked_widths else art_shoulder_w
    body_scale = art_shoulder_w / max(1.0, median_tracked_w)
    print(f"body_scale={body_scale:.3f}", file=sys.stderr)

    frame_paths = []
    for i, p in enumerate(pose_list):
        if p is None:
            continue
        l_upper_angle = math.degrees(math.atan2(p["l_el"][1] - p["l_sh"][1], p["l_el"][0] - p["l_sh"][0]))
        l_fore_angle = math.degrees(math.atan2(p["l_wr"][1] - p["l_el"][1], p["l_wr"][0] - p["l_el"][0]))
        r_upper_angle = math.degrees(math.atan2(p["r_el"][1] - p["r_sh"][1], p["r_el"][0] - p["r_sh"][0]))
        r_fore_angle = math.degrees(math.atan2(p["r_wr"][1] - p["r_el"][1], p["r_wr"][0] - p["r_el"][0]))

        l_upper_len = math.hypot(p["l_el"][0] - p["l_sh"][0], p["l_el"][1] - p["l_sh"][1]) * body_scale
        l_fore_len = math.hypot(p["l_wr"][0] - p["l_el"][0], p["l_wr"][1] - p["l_el"][1]) * body_scale
        r_upper_len = math.hypot(p["r_el"][0] - p["r_sh"][0], p["r_el"][1] - p["r_sh"][1]) * body_scale
        r_fore_len = math.hypot(p["r_wr"][0] - p["r_el"][0], p["r_wr"][1] - p["r_el"][1]) * body_scale

        canvas = render_frame(
            torso, head, torso_dest, l_shoulder, r_shoulder,
            l_upper_angle, l_fore_angle, r_upper_angle, r_fore_angle,
            l_upper_len, l_fore_len, r_upper_len, r_fore_len,
            l_upper_nat_angle, l_fore_nat_angle, r_upper_nat_angle, r_fore_nat_angle,
            "left_open_palm", "right_thumbs_up",
        )
        out_path = os.path.join(OUT_FRAMES, f"f{i:04d}.png")
        canvas.convert("RGB").save(out_path)
        frame_paths.append(out_path)
        if i % 10 == 0:
            print(f"frame {i}", file=sys.stderr)

    print(f"Rendered {len(frame_paths)} frames to {OUT_FRAMES}", file=sys.stderr)


if __name__ == "__main__":
    main()
