#!/usr/bin/env python3
"""
SIDE EXPERIMENT, take 4: proper affine-matrix rigging instead of hand-rolled
per-limb trigonometry. Each piece gets a single 2D affine matrix (rotate +
uniform scale + translate) computed from its own two local pivot points and
its target world position/angle/length, then PIL's Image.transform(AFFINE)
warps the piece directly onto the canvas in one mathematically clean step -
no pad-and-rotate bookkeeping, no separately-tracked "where did the distal
point end up" offset math to keep in sync by hand.

Uses auto-detected pivots (same heuristic as before: top/bottom row alpha
centroid) unless a manual pivot JSON is supplied via PIVOT_JSON env var -
built to drop in exact hand-marked coordinates later without other changes.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with pillow --with numpy python3 scripts/spike_rigged_render_v2.py
"""
import json
import math
import os
import sys

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spike_cartoon_avatar import face_metrics, draw_face_features

mp_holistic = mp.solutions.holistic
PL = mp_holistic.PoseLandmark

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"
PARTS = f"{ROOT}/data/zho/spike_mediapipe/avatar_parts"
CLIP = os.environ.get("SPIKE_CLIP", f"{ROOT}/data/zho/spike_mediapipe/trimmed/alif_active.mp4")
OUT_FRAMES = os.environ.get("SPIKE_OUT_FRAMES", f"{ROOT}/data/zho/spike_mediapipe/rigged/frames_v2")
PIVOT_JSON = os.environ.get("PIVOT_JSON")
os.makedirs(OUT_FRAMES, exist_ok=True)

CANVAS = (800, 900)
BG = (240, 246, 250, 255)
BAND = 6


# ---------- 2D affine matrix helpers (3x3 homogeneous) ----------

def mat_identity():
    return np.eye(3)


def mat_translate(tx, ty):
    m = np.eye(3)
    m[0, 2], m[1, 2] = tx, ty
    return m


def mat_rotate(theta):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def mat_scale(s):
    return np.array([[s, 0, 0], [0, s, 0], [0, 0, 1]])


def apply(m, pt):
    v = m @ np.array([pt[0], pt[1], 1.0])
    return (v[0], v[1])


def piece_placement_matrix(local_prox, local_dist, target_pos, target_angle, target_len):
    """The single matrix that places a piece so its local proximal pivot
    lands at target_pos, its proximal->distal axis points at target_angle,
    and that axis is scaled to target_len. Built as: undo the piece's own
    natural rotation/position -> scale -> rotate to target -> translate to
    target position. Read right-to-left (standard matrix convention)."""
    natural_len = math.hypot(local_dist[0] - local_prox[0], local_dist[1] - local_prox[1])
    natural_angle = math.atan2(local_dist[1] - local_prox[1], local_dist[0] - local_prox[0])
    scale = target_len / max(1.0, natural_len)

    M = mat_translate(*target_pos)
    M = M @ mat_rotate(target_angle)
    M = M @ mat_scale(scale)
    M = M @ mat_rotate(-natural_angle)
    M = M @ mat_translate(-local_prox[0], -local_prox[1])
    return M


def warp_piece_onto(canvas_rgba, piece, M):
    """Warps `piece` by forward matrix M directly onto canvas_rgba (in
    place) using PIL's affine transform, which wants the inverse mapping
    (output pixel -> input pixel) - computed once via matrix inverse
    rather than hand-derived per case."""
    M_inv = np.linalg.inv(M)
    coeffs = (M_inv[0, 0], M_inv[0, 1], M_inv[0, 2],
              M_inv[1, 0], M_inv[1, 1], M_inv[1, 2])
    layer = piece.transform(canvas_rgba.size, Image.AFFINE, coeffs, resample=Image.BICUBIC)
    canvas_rgba.alpha_composite(layer)


# ---------- pivot detection (auto, or from manual JSON) ----------

def load(name):
    return Image.open(os.path.join(PARTS, f"{name}.png")).convert("RGBA")


def auto_pivots(piece):
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


MANUAL_PIVOTS = json.load(open(PIVOT_JSON)) if PIVOT_JSON else None


def get_pivots(name, piece, point_names):
    """point_names e.g. ("shoulder","elbow") or ("elbow","wrist") or
    ("wrist",) for hands. Falls back to auto-detection per point if a
    manual entry is missing."""
    if MANUAL_PIVOTS and name in MANUAL_PIVOTS:
        entry = MANUAL_PIVOTS[name]
        pts = [tuple(entry[p]) if entry.get(p) else None for p in point_names]
        if all(p is not None for p in pts):
            return tuple(pts) if len(pts) > 1 else (pts[0], pts[0])
    prox, dist = auto_pivots(piece)
    return (prox, dist) if len(point_names) > 1 else (prox, prox)


# ---------- rendering ----------

def render_frame(torso, head, torso_dest, l_shoulder, r_shoulder,
                  angles_lengths, hand_names, face_metrics_data):
    canvas = Image.new("RGBA", CANVAS, BG)
    canvas.alpha_composite(torso, dest=torso_dest)
    head_dest = (CANVAS[0] // 2 - head.width // 2, torso_dest[1] - head.height + 45)
    canvas.alpha_composite(head, dest=head_dest)

    def build_arm(prefix, shoulder_xy, upper_angle, fore_angle, upper_len, fore_len, hand_angle, hand_name):
        upper = load(f"{prefix}_upper_arm")
        u_prox, u_dist = get_pivots(f"{prefix}_upper_arm", upper, ("shoulder", "elbow"))
        M_u = piece_placement_matrix(u_prox, u_dist, shoulder_xy, upper_angle, upper_len)
        warp_piece_onto(canvas, upper, M_u)
        elbow_xy = apply(M_u, u_dist)

        fore = load(f"{prefix}_forearm")
        f_prox, f_dist = get_pivots(f"{prefix}_forearm", fore, ("elbow", "wrist"))
        M_f = piece_placement_matrix(f_prox, f_dist, elbow_xy, fore_angle, fore_len)
        warp_piece_onto(canvas, fore, M_f)
        wrist_xy = apply(M_f, f_dist)

        hand = load(hand_name)
        h_prox, _ = get_pivots(hand_name, hand, ("wrist",))
        # use the real tracked hand_angle (oriented using wrist-to-index base vector)
        M_h = piece_placement_matrix(h_prox, (h_prox[0] + 30, h_prox[1]), wrist_xy, hand_angle, 30)
        warp_piece_onto(canvas, hand, M_h)

    l_upper_angle, l_fore_angle, l_upper_len, l_fore_len, l_hand_angle = angles_lengths["left"]
    r_upper_angle, r_fore_angle, r_upper_len, r_fore_len, r_hand_angle = angles_lengths["right"]
    build_arm("left", l_shoulder, l_upper_angle, l_fore_angle, l_upper_len, l_fore_len, l_hand_angle, hand_names["left"])
    build_arm("right", r_shoulder, r_upper_angle, r_fore_angle, r_upper_len, r_fore_len, r_hand_angle, hand_names["right"])

    # Draw moving face features dynamically on top of the rigged head
    if face_metrics_data:
        open_cv_image = np.array(canvas)
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2BGRA)
        face_c = (head_dest[0] + head.width // 2, head_dest[1] + int(head.height * 0.52))
        face_r = int(head.width * 0.28)
        draw_face_features(open_cv_image, face_c, face_r, face_metrics_data)
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGRA2RGBA)
        canvas = Image.fromarray(open_cv_image)

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

    cap = cv2.VideoCapture(CLIP)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def classify_hand_shape(hand_pts):
        if not hand_pts:
            return "open_palm"
        
        def dist(p1, p2):
            return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            
        wrist = hand_pts[0]
        
        def is_finger_extended(base_idx, pip_idx, tip_idx):
            d_pip = dist(hand_pts[pip_idx], wrist)
            d_tip = dist(hand_pts[tip_idx], wrist)
            return d_tip > d_pip
            
        index_ext = is_finger_extended(5, 6, 8)
        middle_ext = is_finger_extended(9, 10, 12)
        ring_ext = is_finger_extended(13, 14, 16)
        pinky_ext = is_finger_extended(17, 18, 20)
        
        # Thumb extension: check distance between thumb tip and index base
        thumb_ext = dist(hand_pts[4], hand_pts[5]) > dist(hand_pts[2], hand_pts[5])
        
        extended_count = sum([index_ext, middle_ext, ring_ext, pinky_ext])
        
        if extended_count >= 3:
            return "open_palm"
        elif index_ext and not middle_ext and not ring_ext and not pinky_ext:
            return "pointing"
        elif thumb_ext and extended_count == 0:
            return "thumbs_up"
        else:
            return "open_palm"

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

                def get_hand_pts(hand_landmarks):
                    if not hand_landmarks:
                        return None
                    return [(hl.x * w, hl.y * h) for hl in hand_landmarks.landmark]

                # screen-left/right swap: see spike_rigged_render.py notes
                pose_list.append({
                    "l_sh": P(PL.RIGHT_SHOULDER), "l_el": P(PL.RIGHT_ELBOW), "l_wr": P(PL.RIGHT_WRIST),
                    "r_sh": P(PL.LEFT_SHOULDER), "r_el": P(PL.LEFT_ELBOW), "r_wr": P(PL.LEFT_WRIST),
                    "l_hand": get_hand_pts(r.right_hand_landmarks),
                    "r_hand": get_hand_pts(r.left_hand_landmarks),
                    "face_metrics": face_metrics(r.face_landmarks.landmark, w, h) if r.face_landmarks else None,
                })
            else:
                pose_list.append(None)
    cap.release()

    def blend_val(a, b, alpha):
        if a is None or b is None:
            return b
        if isinstance(a, dict):
            return {k: blend_val(a[k], b[k], alpha) for k in a}
        if isinstance(a, (list, tuple)):
            if len(a) > 0 and not isinstance(a[0], (list, tuple)):
                return tuple(av * (1 - alpha) + bv * alpha for av, bv in zip(a, b))
            return tuple(blend_val(av, bv, alpha) for av, bv in zip(a, b))
        return a * (1 - alpha) + b * alpha

    def smooth(lst, alpha=0.25):
        out, prev = [None] * len(lst), None
        for i, v in enumerate(lst):
            if v is None:
                prev = None
                continue
            if prev is None:
                out[i] = v
            else:
                out[i] = {k: blend_val(prev[k], v[k], alpha) for k in v}
            prev = out[i]
        return out

    pose_list = smooth(pose_list)

    art_shoulder_w = abs(r_shoulder[0] - l_shoulder[0])
    tracked_widths = [abs(p["r_sh"][0] - p["l_sh"][0]) for p in pose_list if p]
    median_tracked_w = float(np.median(tracked_widths)) if tracked_widths else art_shoulder_w
    body_scale = art_shoulder_w / max(1.0, median_tracked_w)
    print(f"body_scale={body_scale:.3f}", file=sys.stderr)

    frame_paths = []
    for i, p in enumerate(pose_list):
        if p is None:
            continue
        angles_lengths = {}
        hand_names = {}
        for side in ("l", "r"):
            sh, el, wr = p[f"{side}_sh"], p[f"{side}_el"], p[f"{side}_wr"]
            upper_angle = math.atan2(el[1] - sh[1], el[0] - sh[0])
            fore_angle = math.atan2(wr[1] - el[1], wr[0] - el[0])
            upper_len = math.hypot(el[0] - sh[0], el[1] - sh[1]) * body_scale
            fore_len = math.hypot(wr[0] - el[0], wr[1] - el[1]) * body_scale

            # calculate the hand orientation angle and classify pose
            hand_pts = p[f"{side}_hand"]
            if hand_pts is not None:
                wrist, index_base = hand_pts[0], hand_pts[5]
                hand_angle = math.atan2(index_base[1] - wrist[1], index_base[0] - wrist[0])
                # Determine correct asset name prefix
                side_prefix = "left" if side == "l" else "right"
                hand_names[side_prefix] = f"{side_prefix}_{classify_hand_shape(hand_pts)}"
            else:
                hand_angle = fore_angle
                side_prefix = "left" if side == "l" else "right"
                hand_names[side_prefix] = f"{side_prefix}_open_palm"

            key = "left" if side == "l" else "right"
            angles_lengths[key] = (upper_angle, fore_angle, upper_len, fore_len, hand_angle)

        canvas = render_frame(
            torso, head, torso_dest, l_shoulder, r_shoulder,
            angles_lengths, hand_names, p.get("face_metrics")
        )
        out_path = os.path.join(OUT_FRAMES, f"f{i:04d}.png")
        canvas.convert("RGB").save(out_path)
        frame_paths.append(out_path)
        if i % 10 == 0:
            print(f"frame {i}", file=sys.stderr)

    print(f"Rendered {len(frame_paths)} frames to {OUT_FRAMES}", file=sys.stderr)


if __name__ == "__main__":
    main()
