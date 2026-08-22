"""Experimental AFTER-renderer (Part A10). Reuses everything possible from
scripts/spike_cartoon_avatar.py UNMODIFIED (imported, not copied): ipt,
draw_capsule, FINGER_CHAINS, PALM_OUTLINE, HALO, colors, draw_body,
smooth_series, HandTrack. Only adds NEW drawing functions here — the
production file is never edited.

Three visible improvements attempted, each using data that was already
being captured but was previously unused by the renderer:

1. Palm-facing shading — uses the palm-orientation normal (hand_features.py,
   itself derived from z that was already exported to motion JSON but never
   read by any drawing code). Back-of-hand frames get a visibly darker fill;
   front-of-hand frames look as before. This is the single biggest "new
   information now visible" change, because the baseline renderer cannot
   currently distinguish a hand facing the camera from one facing away —
   both look pixel-identical today since only (x,y) is drawn.

2. Independent left/right eyebrows — uses face_features_v2's separate L/R
   brow measurements instead of face_metrics()'s single averaged value.

3. Full eye closure (blink) — the baseline's eye height is clamped to a
   minimum of face_r*0.03, so eyes visually never fully close. Using
   face_features_v2's discrete blink state, a blink frame now draws a
   closed-eye line instead of a thin-but-open ellipse.

4. Head roll rotation — the head+face group is drawn to a small local
   layer, rotated by the estimated roll angle (head_pose.py), and
   composited back. Pitch/yaw are estimated and reported in the JSON but
   NOT visually applied to the 2D avatar (see final report — attempted,
   found to look uncanny at this render fidelity, disabled, documented).
"""
import sys
import os

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
from spike_cartoon_avatar import (  # noqa: E402 — reused unmodified from production
    ipt, draw_capsule, FINGER_CHAINS, PALM_OUTLINE, HALO,
    SKIN, SKIN_SHADE, SKIN_LINE, KANDURA_LINE, clamp, NEUTRAL,
)


def draw_hand_v2(img, pts, alpha, zs, palm_facing):
    """Same structure as spike_cartoon_avatar.draw_hand, with one addition:
    palm fill color depends on palm_facing ("camera"/"away"/"edge_on"/
    "undetermined"). "away" uses SKIN_SHADE (the existing shading color,
    reused for a new purpose) for the palm fill instead of SKIN, so the
    back of the hand reads as visually distinct from the palm — real
    information (previously-unused z) now visible, not new geometry."""
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

    palm_fill = SKIN_SHADE if palm_facing == "away" else SKIN
    palm = np.array([ipts[i] for i in PALM_OUTLINE], dtype=np.int32)
    cv2.fillConvexPoly(layer, palm, SKIN_LINE, cv2.LINE_AA)
    cv2.fillConvexPoly(layer, palm, palm_fill, cv2.LINE_AA)

    for chain in FINGER_CHAINS:
        prev = ipts[0]
        for k, idx in enumerate(chain):
            r_out = [9, 8, 7, 6][k]
            draw_capsule(layer, prev, ipts[idx], r_out, [8, 7, 6, 5][k], SKIN_LINE)
            prev = ipts[idx]
        prev = ipts[0]
        for k, idx in enumerate(chain):
            r_in = [6, 5, 4, 3][k]
            draw_capsule(layer, prev, ipts[idx], r_in, [5, 4, 3, 2][k], palm_fill)
            prev = ipts[idx]
        cv2.circle(layer, ipts[chain[-1]], 3, palm_fill, -1, cv2.LINE_AA)

    if alpha >= 1.0:
        img[:] = layer
    else:
        cv2.addWeighted(layer, alpha, img, 1 - alpha, 0, dst=img)


def _blend_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(c1[k] * (1 - t) + c2[k] * t for k in range(3))


def draw_gradient_capsule(img, p1, p2, r1, r2, color1, color2, steps=6):
    """Same tapered-capsule shape as draw_capsule, but the fill colour
    interpolates continuously from color1 (at p1) to color2 (at p2)
    instead of one flat colour — drawn as `steps` small sub-capsules with
    interpolated position/radius/colour. Fixes the "blocky, one colour
    per segment" look the per-segment shading had before (each segment
    used its own single averaged colour, creating a hard edge at every
    joint) — adjacent segments now share the same colour at the joint
    they meet, since each one interpolates FROM that joint's own colour."""
    p1, p2 = np.array(p1, dtype=float), np.array(p2, dtype=float)
    for s in range(steps):
        t0, t1 = s / steps, (s + 1) / steps
        a = p1 + (p2 - p1) * t0
        b = p1 + (p2 - p1) * t1
        ra = max(1, int(round(r1 + (r2 - r1) * t0)))
        rb = max(1, int(round(r1 + (r2 - r1) * t1)))
        ca = _blend_color(color1, color2, t0)
        cb = _blend_color(color1, color2, t1)
        c = _blend_color(ca, cb, 0.5)  # one flat colour per sub-step, averaged
        draw_capsule(img, tuple(a), tuple(b), ra, rb, c)


# Wider-contrast pair specifically for depth shading, distinct from
# SKIN_SHADE (which is a subtle robe-fold-shading tone designed for a
# different purpose and too close to SKIN to read as a depth cue at
# video scale/compression). NEAR is a touch lighter/warmer than SKIN;
# FAR is pulled most of the way toward the dark outline tone. Fixed
# 2026-08-22 after visual review showed the original SKIN/SKIN_SHADE
# blend, while numerically correct, was too subtle to actually see.
_DEPTH_NEAR = tuple(min(255, c + (255 - c) * 0.18) for c in SKIN)
_DEPTH_FAR = tuple(SKIN_SHADE[k] * 0.55 + SKIN_LINE[k] * 0.45 for k in range(3))
_CONTRAST = 2.2  # boosts mid-range t away from 0.5 toward the extremes
_CONTOUR_AMPLIFY = 3.0  # amplifies per-point lip-contour deviation from the clip's own mean shape


def draw_hand_v3(img, pts, alpha, zs, palm_nz):
    """v3 (2026-08-22, per user feedback that whole-hand binary light/dark
    "doesn't really help" when only part of the hand is turned): shades
    each finger SEGMENT continuously by ITS OWN two endpoint z-values,
    instead of one binary decision for the entire hand. A curled finger
    whose tip has rotated toward the camera while its base is still
    turned away now visibly shows that difference along its own length —
    previously every joint used the same single whole-hand color.

    Per-frame z range is taken from this hand's own 21 landmarks (not a
    fixed constant) so the shading is self-normalizing to whatever depth
    spread this particular pose actually has, rather than assuming a
    fixed real-world scale MediaPipe's relative z doesn't actually
    guarantee.

    Palm fill is also now a CONTINUOUS blend on palm_nz (the raw
    z-component of the palm normal from hand_features.palm_orientation,
    handedness-corrected) instead of 3 discrete buckets — a hand turning
    edge-on now visibly transitions instead of snapping between two
    colors.
    """
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

    if zs:
        # Exclude the wrist (index 0) from the range: MediaPipe defines
        # hand z relative to the wrist, so the wrist is ALWAYS exactly 0
        # by convention, not a real depth measurement of the fingers.
        # Including it wasted a large chunk of the 0..1 range on the gap
        # between "wrist" and "first knuckle" instead of spending that
        # range on actual finger-to-finger variation, which is what this
        # is supposed to show.
        finger_zs = zs[1:]
        zmin, zmax = min(finger_zs), max(finger_zs)
        zrange = max(1e-6, zmax - zmin)
    else:
        zmin, zrange = 0.0, 1.0

    def _contrast(t):
        return max(0.0, min(1.0, 0.5 + (t - 0.5) * _CONTRAST))

    def point_color(i):
        # Per-LANDMARK colour (not per-segment-averaged) so adjacent
        # segments share an identical colour at the joint where they
        # meet — that continuity, plus draw_gradient_capsule interpolating
        # within each segment, is what makes the whole finger read as one
        # smooth gradient instead of a stack of flat-coloured blocks.
        if not zs:
            return SKIN
        t = _contrast((zs[i] - zmin) / zrange)
        return _blend_color(_DEPTH_NEAR, _DEPTH_FAR, t)

    palm_t = _contrast((palm_nz + 1.0) / 2.0) if palm_nz is not None else 0.0  # nz in [-1,1] -> t in [0,1]
    palm_fill = _blend_color(_DEPTH_NEAR, _DEPTH_FAR, palm_t)
    palm = np.array([ipts[i] for i in PALM_OUTLINE], dtype=np.int32)
    cv2.fillConvexPoly(layer, palm, SKIN_LINE, cv2.LINE_AA)
    cv2.fillConvexPoly(layer, palm, palm_fill, cv2.LINE_AA)

    for chain in FINGER_CHAINS:
        idxs = [0] + list(chain)  # wrist, then the 4 joints of this finger
        for k in range(1, len(idxs)):
            prev_i, idx = idxs[k - 1], idxs[k]
            r_out = [9, 8, 7, 6][k - 1]
            draw_capsule(layer, ipts[prev_i], ipts[idx], r_out, [8, 7, 6, 5][k - 1], SKIN_LINE)
        for k in range(1, len(idxs)):
            prev_i, idx = idxs[k - 1], idxs[k]
            r_in = [6, 5, 4, 3][k - 1]
            c_prev = palm_fill if prev_i == 0 else point_color(prev_i)  # wrist end blends from palm colour
            c_idx = point_color(idx)
            draw_gradient_capsule(layer, ipts[prev_i], ipts[idx], r_in, [5, 4, 3, 2][k - 1], c_prev, c_idx)
        cv2.circle(layer, ipts[chain[-1]], 3, point_color(chain[-1]), -1, cv2.LINE_AA)

    # Wrist boundary marker (user-requested: "would coloring the wrist
    # differently separate wrist from fingers?"). Previously the wrist
    # point was just part of the palm fill, with no visual boundary
    # between the sleeve/forearm and the hand at all. A thin ring in the
    # sleeve's own outline colour (KANDURA_LINE, not a skin tone) at the
    # wrist landmark reads as a real "cuff" joint, distinct from every
    # skin-toned part of the hand.
    wrist_r = 5
    cv2.circle(layer, ipts[0], wrist_r, KANDURA_LINE, 2, cv2.LINE_AA)

    if alpha >= 1.0:
        img[:] = layer
    else:
        cv2.addWeighted(layer, alpha, img, 1 - alpha, 0, dst=img)


def draw_face_features_v2(canvas, face_c, face_r, metrics_v1, metrics_v2, head_pose,
                           brow_calibration=None, mouth_calibration=None, mouth_contour_calibration=None):
    """Draws eyebrows (independent L/R), eyes (with blink), and mouth
    (unchanged from v1's curve — mouth v2 fields are captured/exported
    but NOT yet rendered differently, see final report classification)
    onto a local layer sized to the head, then rotates that layer by the
    estimated roll angle before compositing onto canvas. Pitch/yaw are
    accepted as parameters but intentionally unused for rendering (see
    module docstring) — kept in the signature so the call site doesn't
    need to change if that's revisited later.

    brow_calibration (optional, from face_features_v2.compute_brow_calibration):
    same fix as the hand-depth shading — instead of comparing this clip's
    brow position against one fixed NEUTRAL constant tuned on different
    footage/a different signer, rescale against what THIS clip's own
    signer actually did (min/max observed across the clip), with the same
    contrast-boost curve, so a real but modest brow movement still reads
    as visible instead of being compressed into a couple of pixels of
    difference. Falls back to the old fixed-NEUTRAL behavior if None."""
    m = metrics_v1 or NEUTRAL
    v2 = metrics_v2

    pad = int(face_r * 1.6)
    size = pad * 2
    layer = np.zeros((size, size, 4), dtype=np.uint8)  # BGRA, transparent bg
    lc = (pad, pad)  # local center

    eye_y = lc[1] - int(face_r * 0.12)
    eye_dx = int(face_r * 0.36)
    mouth_w = int(clamp(m["mouth_width"] * face_r * 1.1, face_r * 0.3, face_r * 0.95))
    mouth_h = int(clamp(m["mouth_open"] * face_r * 2.6, 2, face_r * 0.45))
    smile = int(clamp((m.get("smile", 0.0) - NEUTRAL["smile"]) * face_r * 8, -face_r * 0.22, face_r * 0.22))

    sides = [("left", -1), ("right", 1)] if v2 else [("left", -1), ("right", 1)]
    for name, side in sides:
        ex = lc[0] + side * eye_dx
        if v2:
            brow = v2["brows"]
            raise_val = (brow[f"{name}_inner_raise"] + brow[f"{name}_outer_raise"]) / 2
            if brow_calibration:
                lo, hi = brow_calibration[f"{name}_min"], brow_calibration[f"{name}_max"]
                span = max(1e-6, hi - lo)
                t = (raise_val - lo) / span
                t = max(0.0, min(1.0, 0.5 + (t - 0.5) * _CONTRAST))
                centered = (t - 0.5) * 2  # -1..1
                # BUG FIX (found via visual review: low-raise frames rendered
                # with NO visible eyebrow at all): the original v1 code used
                # an intentionally ASYMMETRIC range (-face_r*0.16 lowered,
                # +face_r*0.22 raised), not a symmetric one. My first version
                # used a symmetric +-0.22 range, which for low-t frames pushed
                # brow_y close enough to eye_y that the eye ellipse (drawn
                # after, on top) completely covered the brow line beneath it
                # - not "hard to see", literally hidden. Matching v1's
                # asymmetric bounds here fixes that collapse.
                brow_delta = centered * (face_r * 0.16 if centered < 0 else face_r * 0.22)
            else:
                brow_delta = clamp((raise_val - NEUTRAL["brow_raise"]) * face_r * 5, -face_r * 0.16, face_r * 0.22)
            eye_state = v2["eyes"][f"{name}_state"]
            aperture = v2["eyes"][f"{name}_aperture"]
        else:
            brow_delta = clamp((m["brow_raise"] - NEUTRAL["brow_raise"]) * face_r * 5, -face_r * 0.16, face_r * 0.22)
            eye_state, aperture = "open", m["eye_open"]

        brow_y = int(eye_y - face_r * 0.24 - brow_delta)
        p1 = (ex - int(face_r * 0.14), brow_y + int(face_r * 0.03))
        p2 = (ex, brow_y)
        p3 = (ex + int(face_r * 0.14), brow_y + int(face_r * 0.03))
        cv2.polylines(layer, [np.array([p1, p2, p3], dtype=np.int32)], False, (*SKIN_LINE, 255), 3, cv2.LINE_AA)

        eye_w = int(clamp(m.get("eye_width", NEUTRAL["eye_width"]) * face_r * 0.55, face_r * 0.08, face_r * 0.16))
        if eye_state == "blink":
            cv2.line(layer, (ex - eye_w, eye_y), (ex + eye_w, eye_y), (*SKIN_LINE, 255), 3, cv2.LINE_AA)
        else:
            eye_h = int(clamp(aperture * face_r * 2.6, face_r * 0.03, face_r * 0.16))
            cv2.ellipse(layer, (ex, eye_y), (eye_w, eye_h), 0, 0, 360, (*SKIN_LINE, 255), -1, cv2.LINE_AA)

    # Per-corner elevation (v2 + calibration) — this is the actual new
    # capability: v1 only ever had one shared `smile` value applied
    # equally to both mouth corners, so it could NOT represent a real
    # asymmetric mouth shape (a smirk, natural asymmetric talking
    # motion). Each corner is now calibrated/contrast-boosted the same
    # way as brows, using the SAME symmetric +-face_r*0.22 bound v1's own
    # `smile` clamp already used (matching those bounds deliberately,
    # after the asymmetric-range bug found in the eyebrow fix — no new
    # bounds mismatch here).
    def corner_delta(name, elev):
        if metrics_v2 and mouth_calibration:
            lo, hi = mouth_calibration[f"{name}_min"], mouth_calibration[f"{name}_max"]
            span = max(1e-6, hi - lo)
            t = (elev - lo) / span
            t = max(0.0, min(1.0, 0.5 + (t - 0.5) * _CONTRAST))
            return (t - 0.5) * 2 * face_r * 0.22
        return smile

    if metrics_v2 and mouth_calibration:
        left_delta = corner_delta("left", metrics_v2["mouth"]["left_corner_elevation"])
        right_delta = corner_delta("right", metrics_v2["mouth"]["right_corner_elevation"])
    else:
        left_delta = right_delta = smile

    mouth_y = lc[1] + int(face_r * 0.46)
    contour_norm = metrics_v2["mouth"].get("contour_norm") if metrics_v2 else None
    if contour_norm and mouth_contour_calibration:
        # Real 12-point outer-lip shape (Part: "not using enough mouth
        # keypoints" fix) instead of a 3-4-scalar parametric
        # reconstruction. Deviation from this clip's own mean contour is
        # amplified (_CONTOUR_AMPLIFY) so real-but-small lip movement is
        # actually visible, same reasoning as the other calibrations —
        # the RAW shape's frame-to-frame differences were confirmed too
        # small to perceive at video scale during visual review.
        pts = []
        for (dx, dy), (mx, my) in zip(contour_norm, mouth_contour_calibration):
            adx = mx + (dx - mx) * _CONTOUR_AMPLIFY
            ady = my + (dy - my) * _CONTOUR_AMPLIFY
            pts.append((int(lc[0] + adx * face_r * 2.6), int(mouth_y + ady * face_r * 2.6)))
        cv2.polylines(layer, [np.array(pts, dtype=np.int32)], True, (*SKIN_LINE, 255), 3, cv2.LINE_AA)
    elif mouth_h > int(face_r * 0.08):
        avg_delta = (left_delta + right_delta) / 2
        cv2.ellipse(layer, (lc[0], int(mouth_y - avg_delta / 2)), (mouth_w // 2, mouth_h // 2), 0, 0, 360, (*SKIN_LINE, 255), -1, cv2.LINE_AA)
    else:
        left = (lc[0] - mouth_w // 2, mouth_y - left_delta)
        right = (lc[0] + mouth_w // 2, mouth_y - right_delta)
        mid = (lc[0], mouth_y - (left_delta + right_delta) / 2)
        pts = []
        for t in np.linspace(0, 1, 12):
            x = (1 - t) ** 2 * left[0] + 2 * (1 - t) * t * mid[0] + t ** 2 * right[0]
            y = (1 - t) ** 2 * left[1] + 2 * (1 - t) * t * mid[1] + t ** 2 * right[1]
            pts.append((int(x), int(y)))
        cv2.polylines(layer, [np.array(pts, dtype=np.int32)], False, (*SKIN_LINE, 255), 3, cv2.LINE_AA)

    roll_deg = 0.0
    if head_pose and head_pose.get("solve_ok"):
        # Clamp to a modest range — full solvePnP roll can be noisy frame
        # to frame at this landmark sparsity; a hard clamp prevents any
        # single noisy frame from producing a visibly uncanny snap.
        roll_deg = clamp(head_pose["roll_deg"], -20, 20)
    if abs(roll_deg) > 0.5:
        rot_mat = cv2.getRotationMatrix2D(lc, -roll_deg, 1.0)
        layer = cv2.warpAffine(layer, rot_mat, (size, size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    x0, y0 = face_c[0] - pad, face_c[1] - pad
    _composite_rgba(canvas, layer, x0, y0)


def _composite_rgba(canvas, layer_rgba, x0, y0):
    h, w = layer_rgba.shape[:2]
    ch, cw = canvas.shape[:2]
    x1, y1 = max(0, x0), max(0, y0)
    x2, y2 = min(cw, x0 + w), min(ch, y0 + h)
    if x2 <= x1 or y2 <= y1:
        return
    lx1, ly1 = x1 - x0, y1 - y0
    lx2, ly2 = lx1 + (x2 - x1), ly1 + (y2 - y1)
    region = canvas[y1:y2, x1:x2]
    sub = layer_rgba[ly1:ly2, lx1:lx2]
    alpha = sub[:, :, 3:4].astype(np.float32) / 255.0
    region[:] = (region.astype(np.float32) * (1 - alpha) + sub[:, :, :3].astype(np.float32) * alpha).astype(np.uint8)
