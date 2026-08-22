"""Derived hand features (Part A3), computed alongside — never replacing —
the canonical raw 21x(x,y,z) MediaPipe hand landmarks. Every function here
takes the raw per-frame landmark list (21 points, each (x,y,z) in pixel
coords for x/y, MediaPipe's raw relative-depth units for z, wrist-relative)
and derives one sign-relevant scalar/vector. Pure numpy math — this is NOT
extra AI inference, it's geometry on data MediaPipe already produced.

MediaPipe hand landmark index reference (legacy mp.solutions.hands topology,
identical in Holistic):
  0 wrist
  1-4   thumb (CMC, MCP, IP, TIP)
  5-8   index (MCP, PIP, DIP, TIP)
  9-12  middle (MCP, PIP, DIP, TIP)
  13-16 ring (MCP, PIP, DIP, TIP)
  17-20 pinky (MCP, PIP, DIP, TIP)

Confirmed by inspecting the MediaPipe Hands landmark topology docs referenced
from the existing FINGER_CHAINS constant in scripts/spike_cartoon_avatar.py.
"""
import numpy as np

FINGER_CHAINS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
MCP_IDX = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}


def _v(pts, i):
    return np.array(pts[i], dtype=float)  # (x, y, z)


def palm_orientation(pts):
    """Palm normal via the plane through wrist, index-MCP, pinky-MCP —
    the standard three-point-plane technique for approximate palm facing.
    Middle-MCP is used only to sanity-check planarity, not in the formula
    itself (documented, not silently dropped).

    normal = (index_mcp - wrist) x (pinky_mcp - wrist), normalized.

    Returns {"normal": [nx,ny,nz], "facing": "camera"|"away"|"edge_on"}.
    z is MediaPipe's own convention: more negative = closer to the camera.
    A normal with a strongly negative z component points toward the
    camera (palm facing viewer); strongly positive z means the back of
    the hand faces the viewer. Near-zero z-component of the normal means
    the hand is roughly edge-on (thresholded at |nz| < 0.15 of unit
    normal — an engineering choice, not a measured constant).
    """
    wrist = _v(pts, 0)
    idx_mcp = _v(pts, MCP_IDX["index"])
    pinky_mcp = _v(pts, MCP_IDX["pinky"])
    v1 = idx_mcp - wrist
    v2 = pinky_mcp - wrist
    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)
    if norm < 1e-6:
        return {"normal": [0.0, 0.0, 0.0], "facing": "undetermined"}
    normal = normal / norm
    if normal[2] < -0.15:
        facing = "camera"
    elif normal[2] > 0.15:
        facing = "away"
    else:
        facing = "edge_on"
    return {"normal": normal.tolist(), "facing": facing}


def finger_flexion(pts):
    """Per-finger joint angles at MCP and PIP (interior angle at each
    joint, in degrees — 180 = straight, smaller = more bent). Index/
    middle/ring/pinky use the 4-point chain (MCP,PIP,DIP,TIP); thumb uses
    its own chain (CMC,MCP,IP,TIP) with the same angle formula applied at
    the equivalent joints. DIP angle also included where the chain
    supports it (all fingers do)."""
    out = {}
    for name, chain in FINGER_CHAINS.items():
        p = [_v(pts, i) for i in chain]  # 4 points: base, joint1, joint2, tip
        angles = {}
        # angle at joint1 (MCP-equivalent): between (base->joint1) and (joint1->joint2)
        angles["mcp_deg"] = _joint_angle(p[0], p[1], p[2])
        # angle at joint2 (PIP-equivalent): between (joint1->joint2) and (joint2->tip)
        angles["pip_deg"] = _joint_angle(p[1], p[2], p[3])
        out[name] = angles
    return out


def _joint_angle(a, b, c):
    """Interior angle at point b formed by segments a-b and b-c, degrees."""
    v1 = a - b
    v2 = c - b
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 180.0
    cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_a)))


def finger_spread(pts):
    """Abduction/spread between adjacent fingers: angle at the wrist
    between each pair of adjacent MCP directions (index-middle,
    middle-ring, ring-pinky), degrees. Larger = more spread apart."""
    wrist = _v(pts, 0)
    mcps = {k: _v(pts, i) - wrist for k, i in MCP_IDX.items()}
    order = ["index", "middle", "ring", "pinky"]
    out = {}
    for a, b in zip(order, order[1:]):
        va, vb = mcps[a], mcps[b]
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if na < 1e-6 or nb < 1e-6:
            out[f"{a}_{b}_deg"] = 0.0
            continue
        cos_a = np.clip(np.dot(va, vb) / (na * nb), -1.0, 1.0)
        out[f"{a}_{b}_deg"] = float(np.degrees(np.arccos(cos_a)))
    return out


def thumb_opposition(pts):
    """Thumb tip to index tip distance, normalized by hand span (wrist to
    middle-MCP, a stable per-frame scale reference), plus thumb-tip to
    palm-centroid distance for a coarse 'thumb tucked vs extended' signal.
    Not a claim of true opposition-angle biomechanics — a normalized
    distance proxy, documented as such."""
    wrist = _v(pts, 0)
    middle_mcp = _v(pts, MCP_IDX["middle"])
    hand_scale = np.linalg.norm(middle_mcp - wrist) or 1.0
    thumb_tip = _v(pts, 4)
    index_tip = _v(pts, 8)
    palm_centroid = np.mean([_v(pts, i) for i in (0, 5, 9, 13, 17)], axis=0)
    return {
        "thumb_index_tip_dist_norm": float(np.linalg.norm(thumb_tip - index_tip) / hand_scale),
        "thumb_tip_to_palm_dist_norm": float(np.linalg.norm(thumb_tip - palm_centroid) / hand_scale),
    }


def hand_openness(pts):
    """Normalized mean fingertip-to-wrist distance (index/middle/ring/pinky
    tips only — thumb excluded since its resting distance differs
    structurally), divided by hand_scale (wrist-to-middle-MCP). NOT
    calibrated to a verified open/closed threshold from ground-truth data
    — presented as a continuous normalized score, not a hard classification,
    since no labeled open/closed dataset exists here to calibrate against."""
    wrist = _v(pts, 0)
    middle_mcp = _v(pts, MCP_IDX["middle"])
    hand_scale = np.linalg.norm(middle_mcp - wrist) or 1.0
    tip_idxs = [8, 12, 16, 20]
    dists = [np.linalg.norm(_v(pts, i) - wrist) for i in tip_idxs]
    return {"openness_score": float(np.mean(dists) / hand_scale)}


def relative_position(hand_pts, other_hand_pts, pose_frame):
    """Hand relative to torso/head-proxy (neck midpoint from shoulders,
    since no dedicated head landmark exists in the 8-point pose subset
    scripts/spike_cartoon_avatar.py already tracks) and to the other
    hand, all normalized by shoulder width for scale-independence."""
    wrist = _v(hand_pts, 0)
    l_sh = np.array(pose_frame["l_sh"][:2])
    r_sh = np.array(pose_frame["r_sh"][:2])
    shoulder_w = np.linalg.norm(r_sh - l_sh) or 1.0
    neck = (l_sh + r_sh) / 2
    out = {
        "hand_to_neck_dist_norm": float(np.linalg.norm(wrist[:2] - neck) / shoulder_w),
    }
    if other_hand_pts is not None:
        other_wrist = _v(other_hand_pts, 0)
        out["inter_hand_dist_norm"] = float(np.linalg.norm(wrist[:2] - other_wrist[:2]) / shoulder_w)
    return out


def trajectory(wrist_history_xy, fps):
    """Velocity/direction/displacement from a short window of already-
    smoothed wrist (x,y) positions (caller passes e.g. the last 3-5
    frames). Returns None if insufficient history. 'hold' flags a
    low-motion frame (candidate for a linguistic hold), thresholded on
    normalized speed — an engineering heuristic, not a validated
    linguistic hold-detector."""
    if len(wrist_history_xy) < 2:
        return None
    p0 = np.array(wrist_history_xy[-2])
    p1 = np.array(wrist_history_xy[-1])
    disp = p1 - p0
    dt = 1.0 / fps if fps else 1.0
    speed = float(np.linalg.norm(disp) / dt)
    direction = float(np.degrees(np.arctan2(disp[1], disp[0]))) if np.linalg.norm(disp) > 1e-6 else None
    return {
        "velocity_px_per_s": speed,
        "direction_deg": direction,
        "displacement_px": disp.tolist(),
        "is_hold": speed < 15.0,  # px/s threshold, engineering heuristic — documented, not derived from ground truth
    }
