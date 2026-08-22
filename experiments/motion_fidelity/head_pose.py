"""Head pose (pitch/yaw/roll) estimation via solvePnP (Part A5).

Standard monocular head-pose technique: correspond a small set of generic
3D face-model points (in an arbitrary head-centered coordinate system, unit
~mm) to their 2D FaceMesh projections, then solve for the rotation that
would produce that 2D projection under an approximate pinhole camera model.

Camera model assumptions (explicit, not hidden):
  - No camera calibration exists for these clips (unknown UAE ZHO studio
    setup), so intrinsics are APPROXIMATED: focal length = image width,
    principal point = image center, zero lens distortion. This is a common,
    reasonable approximation for near-frontal talking-head footage, but it
    is an approximation — angles are directionally reliable, not
    metrologically precise. Stated explicitly, not glossed over.

3D model points (arbitrary head-centered units, roughly proportional to
average adult face geometry, a widely-used generic reference set — not
derived from this project's own signers):
  nose tip      ( 0.0,   0.0,   0.0)
  chin          ( 0.0, -63.6, -12.5)
  left eye outer(-43.3, 32.7, -26.0)
  right eye outer(43.3, 32.7, -26.0)
  left mouth corner (-28.9, -28.9, -24.1)
  right mouth corner (28.9, -28.9, -24.1)

Coordinate convention reported: yaw+ = head turned toward the signer's own
right (screen-left, mirrored per the existing project convention already
documented in AVATAR_HANDOFF.md), pitch+ = chin down (nodding), roll+ =
head tilted toward the signer's own right shoulder. These follow OpenCV's
solvePnP rotation-vector convention converted to Euler angles via the
standard rotation-matrix decomposition; not independently cross-validated
against a ground-truth IMU in this experiment.
"""
import numpy as np
import cv2

_NOSE_TIP, _CHIN = 1, 152
_L_EYE_OUTER, _R_EYE_OUTER = 33, 263
_MOUTH_L, _MOUTH_R = 61, 291

_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -63.6, -12.5),
    (-43.3, 32.7, -26.0),
    (43.3, 32.7, -26.0),
    (-28.9, -28.9, -24.1),
    (28.9, -28.9, -24.1),
], dtype=np.float64)


def estimate_head_pose(landmarks, w, h):
    """Returns {"pitch_deg", "yaw_deg", "roll_deg", "solve_ok"} or
    solve_ok=False (never fabricates angles when solvePnP fails)."""
    idxs = [_NOSE_TIP, _CHIN, _L_EYE_OUTER, _R_EYE_OUTER, _MOUTH_L, _MOUTH_R]
    image_points = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in idxs], dtype=np.float64)

    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1],
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))

    ok, rvec, _ = cv2.solvePnP(_MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
                                flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return {"pitch_deg": None, "yaw_deg": None, "roll_deg": None, "solve_ok": False}

    rmat, _ = cv2.Rodrigues(rvec)
    sy = (rmat[0, 0] ** 2 + rmat[1, 0] ** 2) ** 0.5
    singular = sy < 1e-6
    if not singular:
        pitch = np.arctan2(rmat[2, 1], rmat[2, 2])
        yaw = np.arctan2(-rmat[2, 0], sy)
        roll = np.arctan2(rmat[1, 0], rmat[0, 0])
    else:
        pitch = np.arctan2(-rmat[1, 2], rmat[1, 1])
        yaw = np.arctan2(-rmat[2, 0], sy)
        roll = 0.0

    return {
        "pitch_deg": float(np.degrees(pitch)),
        "yaw_deg": float(np.degrees(yaw)),
        "roll_deg": float(np.degrees(roll)),
        "solve_ok": True,
    }
