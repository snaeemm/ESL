"""Derived upper-body features (Part A6) from the existing 8-point pose
subset already tracked in scripts/spike_cartoon_avatar.py (l_sh, r_sh,
l_el, r_el, l_wr, r_wr, l_hip, r_hip) — no new landmarks, pure geometry
on data already extracted.

Note on what's NOT attempted: forward/back upper-body movement (true
depth translation, not just rotation) is NOT derived here — the 8-point
subset carries per-landmark z (relative depth, wrist-relative-ish per
MediaPipe Pose convention), but with only shoulders/elbows/wrists/hips and
no fixed reference plane calibrated per-clip, distinguishing "torso moved
closer to camera" from "landmark z noise" is not reliable with this data
alone. REJECT/UNSTABLE for that specific claim; torso LEAN (a 2D-plane
rotation-like signal, not translation) IS derived below and is stable.
"""
import numpy as np


def torso_lean(pose_frame):
    """Angle of the shoulder-midpoint-to-hip-midpoint line from vertical,
    degrees. 0 = perfectly upright. Positive = leaning toward the
    signer's own right (screen-left, per the project's existing mirroring
    convention)."""
    l_sh = np.array(pose_frame["l_sh"][:2])
    r_sh = np.array(pose_frame["r_sh"][:2])
    l_hip = np.array(pose_frame["l_hip"][:2])
    r_hip = np.array(pose_frame["r_hip"][:2])
    shoulder_mid = (l_sh + r_sh) / 2
    hip_mid = (l_hip + r_hip) / 2
    v = shoulder_mid - hip_mid
    angle = np.degrees(np.arctan2(v[0], -v[1]))  # 0 = straight up
    return float(angle)


def shoulder_asymmetry(pose_frame):
    """Vertical difference between shoulders, normalized by shoulder
    width — a proxy for shoulder shrug/tilt, not a claim of true 3D
    rotation."""
    l_sh = np.array(pose_frame["l_sh"][:2])
    r_sh = np.array(pose_frame["r_sh"][:2])
    shoulder_w = np.linalg.norm(r_sh - l_sh) or 1.0
    return float((r_sh[1] - l_sh[1]) / shoulder_w)


def body_features(pose_frame):
    return {
        "torso_lean_deg": torso_lean(pose_frame),
        "shoulder_asymmetry_norm": shoulder_asymmetry(pose_frame),
        "forward_back_translation": None,  # REJECT/UNSTABLE — see module docstring
    }
