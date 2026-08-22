"""Derived face / non-manual features (Part A4) — a wider, still-stable
subset of the 468-point FaceMesh, computed independently per side (unlike
the existing scripts/spike_cartoon_avatar.py:face_metrics(), which averages
L/R into single scalars). This does NOT touch face_metrics() — it is an
additional, separate feature set (face_features_v2) for experimentation.

Landmark indices below are standard MediaPipe FaceMesh indices, extending
the existing set already used in spike_cartoon_avatar.py (_FM_* constants)
rather than inventing a new numbering scheme.

Explicitly NOT attempted / rejected here, with reasons:
  - Gaze/iris direction: MediaPipe Holistic is run with
    refine_face_landmarks=False (confirmed in scripts/spike_cartoon_avatar.py
    main()), which is the flag that enables iris landmarks (468-477). Without
    it, no iris landmarks exist in the output AT ALL — not noisy, absent.
    Gaze is NOT available from current data. Enabling refine_face_landmarks
    would add real MediaPipe inference cost and is a separate, larger change
    outside this experiment's scope (see final report §12/§16).
  - Lip protrusion (z-depth of lip landmarks): tested informally against
    the two z-only-available protrusion candidates and found too noisy
    frame-to-frame relative to the signal (z jitter comparable in magnitude
    to expected protrusion movement) to trust without dedicated smoothing
    tuning beyond this experiment's scope — REJECT/UNSTABLE, not implemented.
"""
import numpy as np

# Existing indices (reused from spike_cartoon_avatar.py, not duplicated
# logic, just referenced for context):
_TOP, _CHIN = 10, 152
_LFACE, _RFACE = 234, 454

# New per-side indices:
_L_BROW_INNER, _L_BROW_OUTER = 55, 105   # left inner/outer brow
_R_BROW_INNER, _R_BROW_OUTER = 285, 334  # right inner/outer brow
_L_EYE_TOP, _L_EYE_BOT, _L_EYE_IN, _L_EYE_OUT = 159, 145, 133, 33
_R_EYE_TOP, _R_EYE_BOT, _R_EYE_IN, _R_EYE_OUT = 386, 374, 362, 263
_MOUTH_TOP, _MOUTH_BOT = 13, 14
_MOUTH_L, _MOUTH_R = 61, 291
_UPPER_LIP_TOP, _LOWER_LIP_BOT = 0, 17  # outer lip contour top/bottom for lip-closure distinct from inner mouth_open

BLINK_THRESHOLD = 0.02   # eye_open (normalized) below this = blink — engineering threshold, not clinically validated
SQUINT_BAND = (0.02, 0.035)  # between blink and neutral-open = squint band


def _P(landmarks, i, w, h):
    lm = landmarks[i]
    return np.array([lm.x * w, lm.y * h])


def compute_brow_calibration(face_v2_list):
    """Per-clip (or per-pooled-sequence) min/max of each brow's raise
    value, computed from frames actually present — the same idea as the
    hand-depth fix: don't compare against one fixed NEUTRAL constant
    tuned on different footage/different signer, stretch to what THIS
    clip's signer actually does. Returns None if no v2 data available
    (caller must fall back to the fixed-NEUTRAL behavior)."""
    lefts, rights = [], []
    for v2 in face_v2_list:
        if v2 is None:
            continue
        b = v2["brows"]
        lefts.append((b["left_inner_raise"] + b["left_outer_raise"]) / 2)
        rights.append((b["right_inner_raise"] + b["right_outer_raise"]) / 2)
    if not lefts:
        return None
    return {
        "left_min": min(lefts), "left_max": max(lefts),
        "right_min": min(rights), "right_max": max(rights),
    }


def face_features_v2(landmarks, w, h):
    P = lambda i: _P(landmarks, i, w, h)
    face_h = np.linalg.norm(P(_TOP) - P(_CHIN)) or 1.0
    face_w = np.linalg.norm(P(_LFACE) - P(_RFACE)) or 1.0

    # Brows — separate L/R, inner and outer raise distinct (existing
    # face_metrics() only has one combined point per side).
    l_brow_inner_raise = float(np.linalg.norm(P(_L_BROW_INNER) - P(_L_EYE_TOP)) / face_h)
    l_brow_outer_raise = float(np.linalg.norm(P(_L_BROW_OUTER) - P(_L_EYE_TOP)) / face_h)
    r_brow_inner_raise = float(np.linalg.norm(P(_R_BROW_INNER) - P(_R_EYE_TOP)) / face_h)
    r_brow_outer_raise = float(np.linalg.norm(P(_R_BROW_OUTER) - P(_R_EYE_TOP)) / face_h)
    brow_asymmetry = float(abs((l_brow_inner_raise + l_brow_outer_raise) -
                                (r_brow_inner_raise + r_brow_outer_raise)))

    # Eyes — separate L/R aperture, blink/squint classification, symmetry.
    l_eye_open = float(np.linalg.norm(P(_L_EYE_TOP) - P(_L_EYE_BOT)) / face_h)
    r_eye_open = float(np.linalg.norm(P(_R_EYE_TOP) - P(_R_EYE_BOT)) / face_h)
    eye_asymmetry = float(abs(l_eye_open - r_eye_open))

    def eye_state(v):
        if v < BLINK_THRESHOLD:
            return "blink"
        if SQUINT_BAND[0] <= v <= SQUINT_BAND[1]:
            return "squint"
        return "open"

    # Mouth — width/open already in face_metrics(); add per-corner
    # elevation (asymmetric smile detection) and lip-closure distinct from
    # inner mouth_open (outer lip contour can be closed while inner
    # landmarks still show a small gap, and vice versa).
    mouth_l, mouth_r = P(_MOUTH_L), P(_MOUTH_R)
    mouth_top, mouth_bot = P(_MOUTH_TOP), P(_MOUTH_BOT)
    mouth_center_y = (mouth_top[1] + mouth_bot[1]) / 2
    l_corner_elev = float((mouth_center_y - mouth_l[1]) / face_h)
    r_corner_elev = float((mouth_center_y - mouth_r[1]) / face_h)
    mouth_corner_asymmetry = float(abs(l_corner_elev - r_corner_elev))
    lip_closure = float(np.linalg.norm(P(_UPPER_LIP_TOP) - P(_LOWER_LIP_BOT)) / face_h)

    return {
        "brows": {
            "left_inner_raise": l_brow_inner_raise, "left_outer_raise": l_brow_outer_raise,
            "right_inner_raise": r_brow_inner_raise, "right_outer_raise": r_brow_outer_raise,
            "asymmetry": brow_asymmetry,
        },
        "eyes": {
            "left_aperture": l_eye_open, "right_aperture": r_eye_open,
            "left_state": eye_state(l_eye_open), "right_state": eye_state(r_eye_open),
            "asymmetry": eye_asymmetry,
            "gaze": None,  # NOT AVAILABLE — refine_face_landmarks=False, no iris landmarks (see module docstring)
        },
        "mouth": {
            "open": float(np.linalg.norm(mouth_top - mouth_bot) / face_h),
            "width": float(np.linalg.norm(mouth_l - mouth_r) / face_w),
            "left_corner_elevation": l_corner_elev, "right_corner_elevation": r_corner_elev,
            "corner_asymmetry": mouth_corner_asymmetry,
            "lip_closure": lip_closure,
            "lip_protrusion": None,  # REJECT/UNSTABLE — see module docstring
        },
    }
