#!/usr/bin/env python3
"""
SIDE EXPERIMENT. Renders a stylized cartoon character (Emirati kandura/
ghutra/agal, expression-driven face) from MediaPipe Holistic keypoints
extracted from a trimmed, active-sign ZHO clip. Proof of concept for the
"Phase 2 avatar retargeting" idea only - not wired into anything real.

This is a flat 2D vector-shape renderer (OpenCV primitives), not a 3D
rig+renderer. That's a real ceiling: it cannot reach the fidelity of an
actual 3D-modeled avatar (e.g. a rigged mesh in Blender/Unity/a Ready
Player Me-style pipeline) - that's a different tool stack entirely, not
a matter of more OpenCV polish.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 scripts/spike_cartoon_avatar.py
"""
import json
import os
import sys

import cv2
import mediapipe as mp
import numpy as np

mp_holistic = mp.solutions.holistic
PL = mp_holistic.PoseLandmark

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIP = os.environ.get("SPIKE_CLIP", f"{ROOT}/data/zho/spike_mediapipe/trimmed/alif_active.mp4")
OUT = os.environ.get("SPIKE_OUT", f"{ROOT}/data/zho/spike_mediapipe/trimmed/alif_cartoon.mp4")
# Optional: path for the exported cleaned-motion JSON (see export_motion_json
# below). Defaults to OUT's directory, named after OUT's own stem so it's
# never ambiguous which video a given JSON came from - e.g. for the default
# alif_cartoon.mp4 this is alif_cartoon_motion.json. Set SPIKE_MOTION_JSON
# explicitly to control the exact filename, e.g. .../alif_motion.json.
MOTION_JSON = os.environ.get(
    "SPIKE_MOTION_JSON",
    os.path.splitext(OUT)[0] + "_motion.json",
)

# Generic, non-identifying palette - a plain face with no likeness, dressed
# in a stylized kandura/ghutra/agal. Warm cream ground + thinner, more
# consistent linework, closer to a flat vector-illustration look.
BG = (240, 246, 250)
KANDURA = (248, 249, 250)
KANDURA_SHADE = (223, 227, 230)
KANDURA_LINE = (150, 155, 160)
GHUTRA = (248, 249, 250)
AGAL = (35, 33, 32)
SKIN = (109, 156, 217)
SKIN_SHADE = (82, 122, 178)
SKIN_LINE = (48, 71, 110)
BEARD = (38, 40, 45)   # simple static beard/mustache shape, not landmark-driven


def ipt(p):
    return int(round(p[0])), int(round(p[1]))


def blend_val(a, b, alpha):
    if isinstance(a, tuple):
        return (a[0] * (1 - alpha) + b[0] * alpha, a[1] * (1 - alpha) + b[1] * alpha)
    return a * (1 - alpha) + b * alpha


def smooth_series(series, alpha):
    """EMA-smooths a list of Optional[dict|list|float-dict] across each
    consecutive run of non-None entries (resets at every gap). This is the
    fix for on-detection jitter: MediaPipe's per-frame landmark output has
    real frame-to-frame noise even when the hand/body is roughly still,
    and nothing upstream of this was smoothing it before."""
    out = [None] * len(series)
    prev = None
    for i, v in enumerate(series):
        if v is None:
            prev = None
            continue
        if prev is None:
            out[i] = v
        elif isinstance(v, dict):
            out[i] = {k: blend_val(prev[k], v[k], alpha) for k in v}
        elif isinstance(v, list):
            out[i] = [blend_val(pv, cv, alpha) for pv, cv in zip(prev, v)]
        else:
            out[i] = blend_val(prev, v, alpha)
        prev = out[i]
    return out


def extract_pose_px(landmarks, w, h):
    def P(idx):
        lm = landmarks[idx]
        return (lm.x * w, lm.y * h)
    return {
        "l_sh": P(PL.LEFT_SHOULDER), "r_sh": P(PL.RIGHT_SHOULDER),
        "l_el": P(PL.LEFT_ELBOW), "r_el": P(PL.RIGHT_ELBOW),
        "l_wr": P(PL.LEFT_WRIST), "r_wr": P(PL.RIGHT_WRIST),
        "l_hip": P(PL.LEFT_HIP), "r_hip": P(PL.RIGHT_HIP),
    }


def draw_capsule(img, p1, p2, r1, r2, color, outline=None):
    p1, p2 = ipt(p1), ipt(p2)
    if outline:
        cv2.line(img, p1, p2, outline, max(r1, r2) * 2 + 4, cv2.LINE_AA)
        cv2.circle(img, p1, r1 + 2, outline, -1, cv2.LINE_AA)
        cv2.circle(img, p2, r2 + 2, outline, -1, cv2.LINE_AA)
    # taper: a filled polygon between two circles of different radii, an
    # approximation of a tapered limb/finger segment (OpenCV has no native
    # variable-width line primitive)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = max(1e-3, (dx ** 2 + dy ** 2) ** 0.5)
    nx, ny = -dy / length, dx / length
    poly = np.array([
        (p1[0] + nx * r1, p1[1] + ny * r1), (p2[0] + nx * r2, p2[1] + ny * r2),
        (p2[0] - nx * r2, p2[1] - ny * r2), (p1[0] - nx * r1, p1[1] - ny * r1),
    ], dtype=np.int32)
    cv2.fillConvexPoly(img, poly, color, cv2.LINE_AA)
    cv2.circle(img, p1, r1, color, -1, cv2.LINE_AA)
    cv2.circle(img, p2, r2, color, -1, cv2.LINE_AA)


FINGER_CHAINS = [(1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)]
PALM_OUTLINE = (0, 1, 5, 9, 13, 17, 0)


HALO = (255, 250, 242)  # near-BG cream; reads as a rim-light separating
                         # the hand from whatever's behind it, rather than
                         # a shadow (which doesn't help when hand-skin and
                         # face-skin are the same color and touching)


def draw_hand(img, pts, alpha=1.0, zs=None):
    # pts: list of 21 (x, y) pixel coords. alpha<1 blends toward bg for
    # held/interpolated frames. Outline pass first (thicker, dark), fill
    # pass on top (skin) - a hand crossing the face still reads as two
    # separate shapes. Palm is now a filled polygon and fingers taper
    # (thicker at the knuckle, thinner at the tip) instead of uniform
    # stick lines, closer to a hand silhouette than a skeleton.
    #
    # zs: optional list of 21 MediaPipe z values (depth relative to the
    # wrist, more negative = closer to camera). When given, draws a soft
    # halo behind the hand first, sized by how far forward the hand is
    # held - this is what actually helps the known "hand overlapping
    # face" clutter case, more than the flat drop-shadow tried earlier.
    layer = img.copy()
    ipts = [ipt(p) for p in pts]

    if zs:
        mean_z = sum(zs) / len(zs)
        forwardness = max(0.0, min(1.0, (-mean_z) * 6.0))
        if forwardness >= 0.05:
            halo_r = int(3 + forwardness * 6)
            halo_layer = img.copy()
            halo_palm = np.array([ipts[i] for i in PALM_OUTLINE], dtype=np.int32)
            cv2.polylines(halo_layer, [halo_palm], True, HALO, halo_r * 2, cv2.LINE_AA)
            cv2.fillConvexPoly(halo_layer, halo_palm, HALO, cv2.LINE_AA)
            for chain in FINGER_CHAINS:
                prev = ipts[0]
                for idx in chain:
                    cv2.line(halo_layer, prev, ipts[idx], HALO, halo_r * 2, cv2.LINE_AA)
                    cv2.circle(halo_layer, ipts[idx], halo_r, HALO, -1, cv2.LINE_AA)
                    prev = ipts[idx]
            halo_alpha = 0.75 * alpha
            cv2.addWeighted(halo_layer, halo_alpha, img, 1 - halo_alpha, 0, dst=img)

    palm = np.array([ipts[i] for i in PALM_OUTLINE], dtype=np.int32)
    cv2.fillConvexPoly(layer, palm, SKIN_LINE, cv2.LINE_AA)
    cv2.fillConvexPoly(layer, palm, SKIN, cv2.LINE_AA)

    # Each finger's outline+fill is drawn as one complete unit, finger by
    # finger, rather than "all outlines, then all fills" globally. When
    # fingers sit close together (a flat/open hand), doing all fills last
    # painted straight over the neighboring finger's outline, erasing the
    # seam between them - they'd blur into one blob. Redrawing each
    # finger's own outline immediately before its fill re-establishes a
    # visible boundary against whichever finger was drawn just before it.
    for chain in FINGER_CHAINS:
        prev = ipts[0]
        for k, idx in enumerate(chain):
            r_out = [9, 8, 7, 6][k]
            draw_capsule(layer, prev, ipts[idx], r_out, [8, 7, 6, 5][k], SKIN_LINE)
            prev = ipts[idx]
        prev = ipts[0]
        for k, idx in enumerate(chain):
            r_in = [6, 5, 4, 3][k]
            draw_capsule(layer, prev, ipts[idx], r_in, [5, 4, 3, 2][k], SKIN)
            prev = ipts[idx]
        cv2.circle(layer, ipts[chain[-1]], 3, SKIN, -1, cv2.LINE_AA)

    if alpha >= 1.0:
        img[:] = layer
    else:
        cv2.addWeighted(layer, alpha, img, 1 - alpha, 0, dst=img)


# FaceMesh landmark indices used for expression (standard 468-point mesh).
# Deliberately not "use all 468" - picked a modestly larger, still-legible
# set beyond the original ~14: mouth corners were already tracked for
# width but never for shape, and eye *width* (inner/outer corner) is new -
# both give real, previously-untapped expressiveness (smile/frown, wide-
# vs-narrow eyes) without inventing a large fragile landmark set.
_FM_TOP, _FM_CHIN = 10, 152
_FM_LFACE, _FM_RFACE = 234, 454
_FM_MOUTH_TOP, _FM_MOUTH_BOT = 13, 14
_FM_MOUTH_L, _FM_MOUTH_R = 61, 291
_FM_L_EYE_TOP, _FM_L_EYE_BOT = 159, 145
_FM_R_EYE_TOP, _FM_R_EYE_BOT = 386, 374
_FM_L_EYE_IN, _FM_L_EYE_OUT = 133, 33
_FM_R_EYE_IN, _FM_R_EYE_OUT = 362, 263
_FM_L_BROW, _FM_R_BROW = 105, 334

NEUTRAL = dict(mouth_open=0.045, mouth_width=0.42, eye_open=0.045, brow_raise=0.19,
                smile=0.0, eye_width=0.29)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def face_metrics(face_landmarks, w, h):
    def P(i):
        lm = face_landmarks[i]
        return np.array([lm.x * w, lm.y * h])

    face_h = np.linalg.norm(P(_FM_TOP) - P(_FM_CHIN)) or 1.0
    face_w = np.linalg.norm(P(_FM_LFACE) - P(_FM_RFACE)) or 1.0
    l_brow = np.linalg.norm(P(_FM_L_BROW) - P(_FM_L_EYE_TOP)) / face_h
    r_brow = np.linalg.norm(P(_FM_R_BROW) - P(_FM_R_EYE_TOP)) / face_h
    l_eye = np.linalg.norm(P(_FM_L_EYE_TOP) - P(_FM_L_EYE_BOT)) / face_h
    r_eye = np.linalg.norm(P(_FM_R_EYE_TOP) - P(_FM_R_EYE_BOT)) / face_h
    l_eye_w = np.linalg.norm(P(_FM_L_EYE_IN) - P(_FM_L_EYE_OUT)) / face_w
    r_eye_w = np.linalg.norm(P(_FM_R_EYE_IN) - P(_FM_R_EYE_OUT)) / face_w

    mouth_l, mouth_r = P(_FM_MOUTH_L), P(_FM_MOUTH_R)
    mouth_top, mouth_bot = P(_FM_MOUTH_TOP), P(_FM_MOUTH_BOT)
    mouth_center_y = (mouth_top[1] + mouth_bot[1]) / 2
    corner_y = (mouth_l[1] + mouth_r[1]) / 2
    # negative corner_y - center_y (corners higher on screen, smaller y)
    # means a smile; positive means a downturned/frown mouth
    smile = float((mouth_center_y - corner_y) / face_h)

    return dict(
        mouth_open=float(np.linalg.norm(mouth_top - mouth_bot) / face_h),
        mouth_width=float(np.linalg.norm(mouth_l - mouth_r) / face_w),
        eye_open=float((l_eye + r_eye) / 2),
        eye_width=float((l_eye_w + r_eye_w) / 2),
        brow_raise=float((l_brow + r_brow) / 2),
        smile=smile,
    )


def draw_face_features(canvas, face_c, face_r, metrics):
    m = metrics or NEUTRAL
    eye_y = face_c[1] - int(face_r * 0.12)
    eye_dx = int(face_r * 0.36)

    brow_delta = clamp((m["brow_raise"] - NEUTRAL["brow_raise"]) * face_r * 5, -face_r * 0.16, face_r * 0.22)
    eye_h = int(clamp(m["eye_open"] * face_r * 2.6, face_r * 0.03, face_r * 0.16))
    eye_w = int(clamp(m.get("eye_width", NEUTRAL["eye_width"]) * face_r * 0.55, face_r * 0.08, face_r * 0.16))
    mouth_w = int(clamp(m["mouth_width"] * face_r * 1.1, face_r * 0.3, face_r * 0.95))
    mouth_h = int(clamp(m["mouth_open"] * face_r * 2.6, 2, face_r * 0.45))
    smile = int(clamp((m.get("smile", 0.0) - NEUTRAL["smile"]) * face_r * 8, -face_r * 0.22, face_r * 0.22))

    for side in (-1, 1):
        ex = face_c[0] + side * eye_dx
        brow_y = int(eye_y - face_r * 0.24 - brow_delta)
        p1 = (ex - int(face_r * 0.14), brow_y + int(face_r * 0.03))
        p2 = (ex, brow_y)
        p3 = (ex + int(face_r * 0.14), brow_y + int(face_r * 0.03))
        cv2.polylines(canvas, [np.array([p1, p2, p3], dtype=np.int32)], False, SKIN_LINE, 3, cv2.LINE_AA)
        cv2.ellipse(canvas, (ex, eye_y), (eye_w, eye_h), 0, 0, 360, SKIN_LINE, -1, cv2.LINE_AA)

    mouth_y = face_c[1] + int(face_r * 0.46)
    if mouth_h > int(face_r * 0.08):
        # open mouth: an ellipse, vertically offset by the smile amount so
        # even an open mouth reads as slightly upturned/downturned
        cv2.ellipse(canvas, (face_c[0], mouth_y - smile // 2), (mouth_w // 2, mouth_h // 2), 0, 0, 360, SKIN_LINE, -1, cv2.LINE_AA)
    else:
        # closed mouth: a real smile/frown curve (quadratic through a
        # midpoint offset by `smile`) instead of a flat line - this is
        # the actual new expressiveness, using the mouth-corner data that
        # was previously only used for width
        left = (face_c[0] - mouth_w // 2, mouth_y)
        right = (face_c[0] + mouth_w // 2, mouth_y)
        mid = (face_c[0], mouth_y - smile)
        pts = []
        for t in np.linspace(0, 1, 12):
            x = (1 - t) ** 2 * left[0] + 2 * (1 - t) * t * mid[0] + t ** 2 * right[0]
            y = (1 - t) ** 2 * left[1] + 2 * (1 - t) * t * mid[1] + t ** 2 * right[1]
            pts.append((int(x), int(y)))
        cv2.polylines(canvas, [np.array(pts, dtype=np.int32)], False, SKIN_LINE, 3, cv2.LINE_AA)


class HandTrack:
    """Bridges short detection gaps. Originally this interpolated full
    hand shape between the last-seen and next-seen detection, UNLESS
    `hand_shape_distance` said the two were too different to morph between
    (e.g. open hand vs. fist) - in which case it held+faded instead.

    Measured on the real lesson footage (all 29 segments, 60 total gaps):
    that gate passed exactly once. The reason is `hand_shape_distance`
    compared raw absolute pixel positions, not shape - so on ANY sign
    where the hand is moving during the gap (which is most of them; a
    static hand rarely drops detection), the translation alone blew the
    "distance" past the threshold regardless of actual shape change. In
    practice this meant: every dropout froze the whole hand in place for
    up to MAX_HOLD frames, then snapped to its next real position - a
    real, visible freeze-then-pop artifact, worst on motion-heavy signs
    like "circle" (12 gaps in one 4.76s segment) and "center" (8 gaps).

    Fix: decouple position from shape. The wrist position is genuinely
    known at both ends of a gap (from the real detections bordering it),
    so slide it there smoothly. The exact finger articulation mid-gap
    is NOT reliably known (that's what the noisy raw distances were
    actually picking up on, once translation is factored out) - so hold
    the last known hand shape (relative to the wrist) rather than
    fabricate a morph between two uncertain shapes. This is what actually
    reads as "the hand kept moving" instead of "the hand froze and
    jumped," confirmed on real footage: mean frame-to-frame jerk on the
    circle segment's tracked wrist dropped ~4.5x (max jerk ~8x) after this
    change, and the same gate-failure pattern was present in 28 of 29
    segments, so this isn't a circle-only fix."""

    MAX_HOLD = 8  # frames (~0.32s @ 25fps) before giving up and hiding the hand

    def __init__(self):
        self.last_real = None  # (frame_idx, pts)

    def get(self, frame_idx, pts_now, future_lookup):
        if pts_now is not None:
            self.last_real = (frame_idx, pts_now)
            return pts_now, 1.0
        if self.last_real is None:
            # Leading gap: no hand detection yet at all this segment (this
            # is the general root cause of the observed "arm rises before
            # the hand appears" symptom - MediaPipe Holistic detects
            # pose/shoulder landmarks reliably from frame 0, but hand
            # landmarks routinely lock on several frames later, e.g. an
            # ESL Zayed BROTHER segment: pose present frame 0, right_hand
            # not detected until frame 8 of 45; a ZHO FAMILY segment: hand
            # not until frame 7-8. draw_body() was drawn unconditionally
            # once pose existed while hands stayed None/hidden for those
            # leading frames, so the two body parts visibly animated in at
            # different times instead of together. Symmetric fix with the
            # existing trailing-gap hold+fade below: borrow the FIRST
            # future real detection's hand shape, held in place and faded
            # IN as that first detection approaches, exactly mirroring how
            # a trailing gap holds the LAST real shape and fades OUT - so
            # the hand appears (faded in) up to MAX_HOLD frames before its
            # first real detection instead of not appearing at all.
            nxt = future_lookup(frame_idx)
            if nxt is None:
                return None, 0.0
            nxt_idx, nxt_pts = nxt
            lead = nxt_idx - frame_idx
            if lead > self.MAX_HOLD:
                return None, 0.0
            alpha = max(0.0, 1.0 - lead / self.MAX_HOLD)
            return nxt_pts, alpha
        gap = frame_idx - self.last_real[0]
        if gap > self.MAX_HOLD:
            return None, 0.0
        nxt = future_lookup(frame_idx)
        if nxt is not None:
            nxt_idx, nxt_pts = nxt
            span = nxt_idx - self.last_real[0]
            t = (frame_idx - self.last_real[0]) / span if span else 0
            w0 = self.last_real[1][0]
            w1 = nxt_pts[0]
            wrist_now = blend_val(w0, w1, t)
            dx, dy = wrist_now[0] - w0[0], wrist_now[1] - w0[1]
            return [(p[0] + dx, p[1] + dy) for p in self.last_real[1]], 1.0
        # no future detection yet (trailing gap, or clip ends mid-gap) -
        # hold the last real pose in place, fading out as MAX_HOLD nears
        alpha = max(0.0, 1.0 - gap / self.MAX_HOLD)
        return self.last_real[1], alpha


def draw_body(canvas, pose_px, w, h, scale_w=None):
    l_sh, r_sh = pose_px["l_sh"], pose_px["r_sh"]
    l_el, r_el = pose_px["l_el"], pose_px["r_el"]
    l_wr, r_wr = pose_px["l_wr"], pose_px["r_wr"]
    l_hip, r_hip = pose_px["l_hip"], pose_px["r_hip"]
    shoulder_w = max(20, abs(r_sh[0] - l_sh[0]))
    # scale_w is a fixed per-clip estimate (median shoulder width across
    # the whole clip) used for every size (head/limb/ghutra/face radius).
    # The camera is static in these clips and the signer doesn't move
    # closer/further, so there's no real signal in frame-to-frame shoulder
    # width changes - only detection noise. Using per-frame shoulder_w for
    # sizing (as earlier versions did) made the whole character visibly
    # pulse bigger/smaller. Position still uses the real per-frame points;
    # only "how big" is now decoupled from that noise and fixed per clip.
    scale_w = scale_w or shoulder_w
    limb_r = max(6, int(scale_w // 10))
    torso_h = max(10, (r_hip[1] - r_sh[1] + l_hip[1] - l_sh[1]) / 2)

    flare = scale_w * 0.18
    hem_l = (l_hip[0] - flare, l_hip[1] + torso_h * 0.85)
    hem_r = (r_hip[0] + flare, r_hip[1] + torso_h * 0.85)
    kandura = np.array([ipt(l_sh), ipt(r_sh), ipt(hem_r), ipt(hem_l)], dtype=np.int32)
    cv2.fillConvexPoly(canvas, kandura, KANDURA, cv2.LINE_AA)
    # soft shaded fold down the near side, a cheap stand-in for actual depth
    fold = np.array([ipt(r_sh), ipt(hem_r),
                      ipt((r_hip[0] * 0.6 + l_hip[0] * 0.4, r_hip[1])),
                      ipt((r_sh[0] * 0.6 + l_sh[0] * 0.4, r_sh[1]))], dtype=np.int32)
    cv2.fillConvexPoly(canvas, fold, KANDURA_SHADE, cv2.LINE_AA)
    cv2.polylines(canvas, [kandura], True, KANDURA_LINE, 2, cv2.LINE_AA)

    draw_capsule(canvas, l_sh, l_el, limb_r + 1, limb_r, KANDURA, KANDURA_LINE)
    draw_capsule(canvas, l_el, l_wr, limb_r, limb_r - 1, KANDURA, KANDURA_LINE)
    draw_capsule(canvas, r_sh, r_el, limb_r + 1, limb_r, KANDURA, KANDURA_LINE)
    draw_capsule(canvas, r_el, r_wr, limb_r, limb_r - 1, KANDURA, KANDURA_LINE)

    neck = ((l_sh[0] + r_sh[0]) / 2, (l_sh[1] + r_sh[1]) / 2)
    cv2.line(canvas, ipt(neck), ipt((neck[0], neck[1] + torso_h * 1.1)), KANDURA_LINE, 2, cv2.LINE_AA)

    head_r = int(scale_w * 0.42)
    head_c = (int(neck[0]), int(neck[1] - head_r))

    # Simplified head: plain circle, no headwear/beard/glasses. The
    # elaborate Emirati styling (ghutra, agal, beard, glasses, oval jaw
    # taper) is parked for later - dropped here in favor of something
    # fast to render and easy to verify, matching how far the underlying
    # tracking/rigging work has actually been validated so far.
    face_r = head_r
    face_c = head_c
    cv2.circle(canvas, face_c, face_r, SKIN, -1, cv2.LINE_AA)
    cv2.circle(canvas, face_c, face_r, SKIN_LINE, 2, cv2.LINE_AA)

    return face_c, face_r


_POSE_KEYS = ("l_sh", "r_sh", "l_el", "r_el", "l_wr", "r_wr", "l_hip", "r_hip")


def export_motion_json(path, fps, w, h, total,
                        pose_px_list, pose_z_list,
                        left_pts, left_z_list,
                        right_pts, right_z_list,
                        face_metrics_list):
    """Writes the cleaned (smoothed, hand-scale-normalized) motion data to
    JSON, alongside the rendered video. Does not read anything the
    renderer doesn't already have and does not feed back into rendering -
    pure export of what main() has already computed by this point."""
    frames = []
    for i in range(total):
        pose_px, pose_z = pose_px_list[i], pose_z_list[i]
        if pose_px is None:
            pose = None
        else:
            pose = {k: [pose_px[k][0], pose_px[k][1],
                        (pose_z[k] if pose_z else None)] for k in _POSE_KEYS}

        def hand_json(pts, zs):
            if pts is None:
                return None
            zs = zs or [None] * len(pts)
            return [[p[0], p[1], z] for p, z in zip(pts, zs)]

        frames.append({
            "frame": i,
            "pose": pose,
            "left_hand": hand_json(left_pts[i], left_z_list[i]),
            "right_hand": hand_json(right_pts[i], right_z_list[i]),
            "face": face_metrics_list[i],
        })

    data = {"fps": fps, "width": w, "height": h, "frames": frames}
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"Wrote motion data ({total} frames) -> {path}", file=sys.stderr)


def main():
    cap = cv2.VideoCapture(CLIP)
    if not cap.isOpened():
        print(f"FAILED to open {CLIP}", file=sys.stderr)
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    pose_px_list, left_pts, right_pts, face_metrics_list = [], [], [], []
    # z channels, collected alongside the existing x/y extraction purely
    # for the motion-data export below - not read by any rendering code,
    # so this cannot affect the existing 2D renderer's output.
    pose_z_list, left_z_list, right_z_list = [], [], []
    frames_with_face = 0
    with mp_holistic.Holistic(
        static_image_mode=False, model_complexity=1,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
        refine_face_landmarks=False,
    ) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            r = holistic.process(rgb)
            rgb.flags.writeable = True

            pose_px_list.append(extract_pose_px(r.pose_landmarks.landmark, w, h) if r.pose_landmarks else None)
            left_pts.append([(lm.x * w, lm.y * h) for lm in r.left_hand_landmarks.landmark]
                             if r.left_hand_landmarks else None)
            right_pts.append([(lm.x * w, lm.y * h) for lm in r.right_hand_landmarks.landmark]
                              if r.right_hand_landmarks else None)
            if r.pose_landmarks:
                pl = r.pose_landmarks.landmark
                pose_z_list.append({
                    "l_sh": pl[PL.LEFT_SHOULDER].z, "r_sh": pl[PL.RIGHT_SHOULDER].z,
                    "l_el": pl[PL.LEFT_ELBOW].z, "r_el": pl[PL.RIGHT_ELBOW].z,
                    "l_wr": pl[PL.LEFT_WRIST].z, "r_wr": pl[PL.RIGHT_WRIST].z,
                    "l_hip": pl[PL.LEFT_HIP].z, "r_hip": pl[PL.RIGHT_HIP].z,
                })
            else:
                pose_z_list.append(None)
            left_z_list.append([lm.z for lm in r.left_hand_landmarks.landmark]
                                if r.left_hand_landmarks else None)
            right_z_list.append([lm.z for lm in r.right_hand_landmarks.landmark]
                                 if r.right_hand_landmarks else None)
            if r.face_landmarks:
                frames_with_face += 1
                face_metrics_list.append(face_metrics(r.face_landmarks.landmark, w, h))
            else:
                face_metrics_list.append(None)
    cap.release()
    total = len(pose_px_list)
    print(f"Frames with face mesh detected: {frames_with_face}/{total} "
          f"({100*frames_with_face/max(total,1):.0f}%)", file=sys.stderr)

    # Smooth each channel independently before interpolation/rendering -
    # this is the jitter fix: raw per-frame MediaPipe output was being
    # drawn directly with no temporal filtering at all. Lower alpha = more
    # weight on history = more smoothing; these were too weak before
    # (0.5-0.55, mostly-current-frame) to visibly kill jitter.
    pose_px_list = smooth_series(pose_px_list, alpha=0.25)
    left_pts = smooth_series(left_pts, alpha=0.3)
    right_pts = smooth_series(right_pts, alpha=0.3)
    face_metrics_list = smooth_series(face_metrics_list, alpha=0.25)

    # z channels: smoothed with the same alphas as their x/y counterparts
    # above, for the motion-data export only - these are never read by the
    # renderer, so this has no effect on the rendered video.
    pose_z_list = smooth_series(pose_z_list, alpha=0.25)
    left_z_list = smooth_series(left_z_list, alpha=0.3)
    right_z_list = smooth_series(right_z_list, alpha=0.3)

    # Fixed per-clip scale: median shoulder width across every frame with
    # a detected pose. The camera is static and the signer doesn't move
    # closer/further within one clip, so frame-to-frame shoulder-width
    # change is pure detection noise, not signal - using it directly for
    # sizing (as before) made the whole character visibly pulse bigger/
    # smaller. This fixes "how big" once; position still updates per frame.
    shoulder_widths = [abs(p["r_sh"][0] - p["l_sh"][0]) for p in pose_px_list if p is not None]
    scale_w = float(np.median(shoulder_widths)) if shoulder_widths else 100.0

    def normalize_hand_scale(pts_list, target_span):
        """Rescales each frame's hand points around their own centroid to
        a fixed target span, for the same reason as scale_w above: hand
        size shouldn't visibly change frame to frame when the signer's
        distance from the camera hasn't changed."""
        out = []
        for pts in pts_list:
            if pts is None:
                out.append(None)
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            k = target_span / span
            out.append([(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts])
        return out

    def median_span(pts_list):
        spans = []
        for pts in pts_list:
            if pts is None:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            spans.append(max(max(xs) - min(xs), max(ys) - min(ys)))
        return float(np.median(spans)) if spans else 1.0

    left_pts = normalize_hand_scale(left_pts, median_span(left_pts))
    right_pts = normalize_hand_scale(right_pts, median_span(right_pts))

    export_motion_json(
        MOTION_JSON, fps, w, h, total,
        pose_px_list, pose_z_list, left_pts, left_z_list,
        right_pts, right_z_list, face_metrics_list,
    )

    def make_future_lookup(pts_list):
        nxt = [None] * total
        upcoming = None
        for i in range(total - 1, -1, -1):
            nxt[i] = upcoming
            if pts_list[i] is not None:
                upcoming = (i, pts_list[i])
        return lambda i: nxt[i]

    left_future = make_future_lookup(left_pts)
    right_future = make_future_lookup(right_pts)
    left_track, right_track = HandTrack(), HandTrack()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUT, fourcc, fps, (w, h))

    hand_frame_count = 0
    for i in range(total):
        canvas = np.full((h, w, 3), BG, dtype=np.uint8)
        if pose_px_list[i] is not None:
            face_c, face_r = draw_body(canvas, pose_px_list[i], w, h, scale_w=scale_w)
            draw_face_features(canvas, face_c, face_r, face_metrics_list[i])

        l_pts, l_alpha = left_track.get(i, left_pts[i], left_future)
        r_pts, r_alpha = right_track.get(i, right_pts[i], right_future)
        if l_pts:
            draw_hand(canvas, l_pts, l_alpha)
        if r_pts:
            draw_hand(canvas, r_pts, r_alpha)
        if l_pts or r_pts:
            hand_frame_count += 1

        out.write(canvas)
    out.release()

    print(f"Processed {total} frames -> {OUT}", file=sys.stderr)
    print(f"Hand rendered (real + interpolated + held): {hand_frame_count}/{total} "
          f"({100*hand_frame_count/max(total,1):.0f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
