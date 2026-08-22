#!/usr/bin/env python3
"""
Body mesh-warp retargeter for the Emirati avatar artwork in this folder.

Pipeline:
  MediaPipe Holistic pose (+ hands)
        -> target joint positions (aligned/scaled into the artwork's canvas)
        -> piecewise-affine warp of avatar_clean_reference.png, triangulated
           over avatar_mesh_rig.json's joints + background grid
        -> procedural per-finger hands (same renderer style as
           spike_cartoon_avatar.py) painted on top at each wrist, since the
           artwork has no calibrated 21-point hand mesh to warp against yet

Everything for this experiment lives in this folder on purpose - source
image, rig, this script, and its output.

Run with:
  uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python \
      --with numpy python3 scripts/test/trying-avatarIwant/avatar_retargeter.py
"""
import json
import os
import sys

import cv2
import mediapipe as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"

REFERENCE_PNG = os.path.join(HERE, "avatar_clean_reference.png")
RIG_JSON = os.path.join(HERE, "avatar_mesh_rig.json")
CLIP = os.environ.get("SPIKE_CLIP", f"{ROOT}/data/zho/spike_mediapipe/trimmed/alif_active.mp4")
OUT = os.environ.get("SPIKE_OUT", os.path.join(HERE, "avatar_retarget_out.mp4"))

mp_holistic = mp.solutions.holistic
PL = mp_holistic.PoseLandmark

# Procedural hand-rendering palette, sampled from the artwork itself so the
# drawn hands match its skin tone/linework instead of the generic spike
# palette.
HAND_SKIN = (107, 150, 217)     # BGR, sampled from the art's face/hand skin
HAND_LINE = (60, 90, 140)       # a darker shade of the same hue for outlines
SLEEVE_ERASE = (233, 246, 248)  # BGR sleeve/kandura white, to paint over the
                                 # art's own (now-misplaced) warped hand


def ipt(p):
    return int(round(p[0])), int(round(p[1]))


# ---------------------------------------------------------------------------
# Rig / triangulation
# ---------------------------------------------------------------------------

def load_rig():
    with open(RIG_JSON) as f:
        rig = json.load(f)
    joints = rig["joints"]
    joint_order = [
        "neck", "left_shoulder", "left_elbow", "left_wrist",
        "right_shoulder", "right_elbow", "right_wrist",
    ]
    joint_pts = [tuple(joints[k]) for k in joint_order]
    grid_pts = [tuple(p) for p in rig["body_controls"]]
    src_pts = joint_pts + grid_pts
    return rig, joint_order, src_pts, len(joint_pts)


def triangulate(points, rect):
    subdiv = cv2.Subdiv2D(rect)
    for p in points:
        subdiv.insert((float(p[0]), float(p[1])))
    triangles = subdiv.getTriangleList()
    idx_by_point = {}
    for i, p in enumerate(points):
        idx_by_point[(round(p[0], 1), round(p[1], 1))] = i

    def nearest_idx(x, y):
        # Subdiv2D can nudge coordinates by float error; snap to the
        # closest known source point instead of exact dict lookup.
        best, best_d = None, 1e18
        for i, p in enumerate(points):
            d = (p[0] - x) ** 2 + (p[1] - y) ** 2
            if d < best_d:
                best, best_d = i, d
        return best

    tris = []
    for t in triangles:
        pts_t = [(t[0], t[1]), (t[2], t[3]), (t[4], t[5])]
        if not all(rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3] for x, y in pts_t):
            continue
        idxs = [idx_by_point.get((round(x, 1), round(y, 1))) for x, y in pts_t]
        idxs = [idxs[k] if idxs[k] is not None else nearest_idx(*pts_t[k]) for k in range(3)]
        tris.append(tuple(idxs))
    return tris


def warp_triangle(src_img, dst_img, src_tri, dst_tri):
    r1 = cv2.boundingRect(np.float32([src_tri]))
    r2 = cv2.boundingRect(np.float32([dst_tri]))
    if r1[2] <= 0 or r1[3] <= 0 or r2[2] <= 0 or r2[3] <= 0:
        return

    src_tri_rect = [(p[0] - r1[0], p[1] - r1[1]) for p in src_tri]
    dst_tri_rect = [(p[0] - r2[0], p[1] - r2[1]) for p in dst_tri]

    src_crop = src_img[r1[1]:r1[1] + r1[3], r1[0]:r1[0] + r1[2]]
    if src_crop.size == 0:
        return

    mat = cv2.getAffineTransform(np.float32(src_tri_rect), np.float32(dst_tri_rect))
    warped = cv2.warpAffine(src_crop, mat, (r2[2], r2[3]), None,
                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    mask = np.zeros((r2[3], r2[2]), dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.int32(dst_tri_rect), 255, cv2.LINE_AA)

    # Target triangle can land partly (or fully) outside the canvas when
    # pose motion is large - clip the paste region to the image bounds
    # before slicing, rather than assuming r2 always fits.
    h, w = dst_img.shape[:2]
    x0, y0 = max(0, r2[0]), max(0, r2[1])
    x1, y1 = min(w, r2[0] + r2[2]), min(h, r2[1] + r2[3])
    if x1 <= x0 or y1 <= y0:
        return
    warped = warped[y0 - r2[1]:y1 - r2[1], x0 - r2[0]:x1 - r2[0]]
    mask = mask[y0 - r2[1]:y1 - r2[1], x0 - r2[0]:x1 - r2[0]]
    mask3 = cv2.merge([mask, mask, mask]).astype(np.float32) / 255.0

    dst_region = dst_img[y0:y1, x0:x1]
    dst_region[:] = (dst_region.astype(np.float32) * (1 - mask3) + warped.astype(np.float32) * mask3).astype(np.uint8)


# ---------------------------------------------------------------------------
# Pose extraction (body + both hands)
# ---------------------------------------------------------------------------

# The rig's "left_shoulder" (x=548) sits on the on-screen-left side of the
# artwork, i.e. it was authored as "viewer's left". MediaPipe's
# PoseLandmark.LEFT_SHOULDER is the subject's own anatomical left, which
# for a person facing the camera appears on-screen-RIGHT. Mapped straight
# through, the rig and the pose data disagree about which side is which -
# that's what was tearing the shoulders/torso apart (not a warp-math bug).
# Swapping here once, at the source, keeps everything downstream consistent.
def extract_pose_px(landmarks, w, h):
    def P(idx):
        lm = landmarks[idx]
        return (lm.x * w, lm.y * h)
    return {
        "neck": tuple((np.array(P(PL.LEFT_SHOULDER)) + np.array(P(PL.RIGHT_SHOULDER))) / 2),
        "left_shoulder": P(PL.RIGHT_SHOULDER), "right_shoulder": P(PL.LEFT_SHOULDER),
        "left_elbow": P(PL.RIGHT_ELBOW), "right_elbow": P(PL.LEFT_ELBOW),
        "left_wrist": P(PL.RIGHT_WRIST), "right_wrist": P(PL.LEFT_WRIST),
    }


# ---------------------------------------------------------------------------
# Procedural finger-articulated hands (same style/technique as
# spike_cartoon_avatar.py's draw_hand, recolored to match this artwork)
# ---------------------------------------------------------------------------

FINGER_CHAINS = [(1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)]
PALM_OUTLINE = (0, 1, 5, 9, 13, 17, 0)


def draw_capsule(img, p1, p2, r1, r2, color, outline=None):
    p1, p2 = ipt(p1), ipt(p2)
    if outline:
        cv2.line(img, p1, p2, outline, max(r1, r2) * 2 + 4, cv2.LINE_AA)
        cv2.circle(img, p1, r1 + 2, outline, -1, cv2.LINE_AA)
        cv2.circle(img, p2, r2 + 2, outline, -1, cv2.LINE_AA)
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


def draw_hand(img, pts):
    ipts = [ipt(p) for p in pts]
    palm = np.array([ipts[i] for i in PALM_OUTLINE], dtype=np.int32)
    cv2.fillConvexPoly(img, palm, HAND_LINE, cv2.LINE_AA)
    cv2.fillConvexPoly(img, palm, HAND_SKIN, cv2.LINE_AA)

    for chain in FINGER_CHAINS:
        prev = ipts[0]
        for k, idx in enumerate(chain):
            r_out = [9, 8, 7, 6][k]
            draw_capsule(img, prev, ipts[idx], r_out, [8, 7, 6, 5][k], HAND_LINE)
            prev = ipts[idx]
        prev = ipts[0]
        for k, idx in enumerate(chain):
            r_in = [6, 5, 4, 3][k]
            draw_capsule(img, prev, ipts[idx], r_in, [5, 4, 3, 2][k], HAND_SKIN)
            prev = ipts[idx]
        cv2.circle(img, ipts[chain[-1]], 3, HAND_SKIN, -1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rig, joint_order, src_pts, n_joints = load_rig()
    canvas_w, canvas_h = rig["canvas"]["width"], rig["canvas"]["height"]
    rig_joints = rig["joints"]

    ref = cv2.imread(REFERENCE_PNG)
    if ref is None:
        print(f"FAILED to load {REFERENCE_PNG}", file=sys.stderr)
        sys.exit(1)
    ref = cv2.resize(ref, (canvas_w, canvas_h))

    # Head + ghutra/agal is pulled out of the piecewise mesh and composited
    # as its own rigid (translate-only) layer instead. The body mesh only
    # has 3 points anchoring the whole head region (canvas-top row + the
    # two shoulder joints) - real arm/shoulder motion is routinely
    # asymmetric, and an affine triangle with a fixed apex and two moving
    # base points shears hard on any asymmetry. That's what was producing
    # the shrunk/detached head: not a bug in the warp math, a structural
    # problem with deforming the head via such a coarse triangle. A rigid
    # translate can't shear at all, which is also just correct for how a
    # ghutra actually behaves - it tracks the head, it doesn't stretch.
    head_cutoff_y = int(rig_joints["neck"][1] + 40)
    head_crop = ref[0:head_cutoff_y, :].copy()
    bg_color = ref[2, 2].astype(np.int16)
    diff = np.abs(head_crop.astype(np.int16) - bg_color).sum(axis=2)
    head_alpha = np.clip((diff - 12) * 8, 0, 255).astype(np.uint8)
    head_alpha = cv2.GaussianBlur(head_alpha, (5, 5), 0)
    # Feather the crop's bottom edge so it blends into the body mesh below
    # instead of cutting through cloth/skin pixels with a hard rectangle
    # edge (a visible seam line even once left/right and scale are correct).
    feather = 50
    ramp = np.linspace(1, 0, feather, dtype=np.float32)
    head_alpha = head_alpha.astype(np.float32)
    head_alpha[-feather:, :] *= ramp[:, None]
    head_alpha = head_alpha.astype(np.uint8)
    head_alpha3 = cv2.merge([head_alpha, head_alpha, head_alpha]).astype(np.float32) / 255.0
    rig_neck_arr = np.array(rig_joints["neck"], dtype=np.float64)

    def composite_head(canvas, neck_target):
        dx, dy = neck_target[0] - rig_neck_arr[0], neck_target[1] - rig_neck_arr[1]
        mat = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted = cv2.warpAffine(head_crop, mat, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        shifted_a = cv2.warpAffine(head_alpha3, mat, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        canvas[:] = (canvas.astype(np.float32) * (1 - shifted_a) + shifted.astype(np.float32) * shifted_a).astype(np.uint8)

    # Subdiv2D's rect is exclusive on the far edge, but the rig's grid
    # deliberately sits exactly on the canvas boundary (e.g. x=canvas_w-1,
    # y=canvas_h-1 corners) - pad it out so those boundary points still
    # count as strictly "inside".
    rect = (0, 0, canvas_w + 2, canvas_h + 2)
    triangles = triangulate(src_pts, rect)
    print(f"Triangulated {len(src_pts)} source points -> {len(triangles)} triangles", file=sys.stderr)

    cap = cv2.VideoCapture(CLIP)
    if not cap.isOpened():
        print(f"FAILED to open {CLIP}", file=sys.stderr)
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    pose_list, left_hand_list, right_hand_list = [], [], []
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
            pose_list.append(extract_pose_px(r.pose_landmarks.landmark, w, h) if r.pose_landmarks else None)
            # Same screen-side swap as extract_pose_px: rig "left" = MediaPipe's
            # anatomical right (on-screen-left for a subject facing camera).
            left_hand_list.append([(lm.x * w, lm.y * h) for lm in r.right_hand_landmarks.landmark]
                                   if r.right_hand_landmarks else None)
            right_hand_list.append([(lm.x * w, lm.y * h) for lm in r.left_hand_landmarks.landmark]
                                    if r.left_hand_landmarks else None)
    cap.release()
    total = len(pose_list)

    # Calibration: align the clip's pose scale/position to the rig's, using
    # the median shoulder width and neck position across frames with a
    # detected pose (single fixed transform per clip, not per frame - same
    # reasoning as spike_cartoon_avatar.py's scale_w: a static camera means
    # per-frame size wobble is noise, not signal).
    widths, necks = [], []
    for p in pose_list:
        if p is None:
            continue
        widths.append(abs(p["right_shoulder"][0] - p["left_shoulder"][0]))
        necks.append(p["neck"])
    if not widths:
        print("No pose detected in clip", file=sys.stderr)
        sys.exit(1)
    clip_shoulder_w = float(np.median(widths))
    clip_neck = np.median(np.array(necks), axis=0)
    rig_shoulder_w = abs(rig_joints["right_shoulder"][0] - rig_joints["left_shoulder"][0])
    rig_neck = np.array(rig_joints["neck"], dtype=np.float64)
    scale = rig_shoulder_w / clip_shoulder_w

    def to_rig_space(p):
        return (rig_neck + (np.array(p) - clip_neck) * scale)

    hand_target_span = 130.0  # px, roughly a hand's size at this canvas scale

    def normalize_hand(pts):
        if pts is None:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
        return pts, span

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUT, fourcc, fps, (canvas_w, canvas_h))

    # The artwork's own hand is baked into the mesh region around the
    # wrist and gets scaled up by the same ~scale factor as the rest of
    # the body, so a fixed small radius left visible fingertip remnants
    # poking out. Scale the erase radius the same way, go wider, and
    # feather the mask (soft blur, not a hard circle) so the erase reads
    # as a shading transition into the sleeve rather than a visible disk.
    hand_erase_r = int(hand_target_span * 0.72 * scale)

    rendered_with_pose = 0
    for i in range(total):
        pose = pose_list[i]
        canvas = ref.copy()

        if pose is not None:
            rendered_with_pose += 1
            target_joints = {k: to_rig_space(pose[k]) for k in joint_order}

            # Background grid points stay put, EXCEPT the two inner points
            # that sit near the elbows (index 6 and 8 in body_controls, at
            # y=250) which partially follow the arm so the torso mesh
            # doesn't tear/stretch too hard at the armpit when the arm
            # lifts. Everything else in body_controls is a fixed anchor
            # (canvas corners/edges), matching how the rig was authored.
            grid_pts = list(rig["body_controls"])
            l_el_delta = target_joints["left_elbow"] - np.array(rig_joints["left_elbow"])
            r_el_delta = target_joints["right_elbow"] - np.array(rig_joints["right_elbow"])
            grid_pts[6] = (np.array(grid_pts[6]) + l_el_delta * 0.35).tolist()
            grid_pts[8] = (np.array(grid_pts[8]) + r_el_delta * 0.35).tolist()

            dst_pts = [tuple(target_joints[k]) for k in joint_order] + [tuple(p) for p in grid_pts]

            warped = ref.copy()
            for tri_idx in triangles:
                s_tri = [src_pts[k] for k in tri_idx]
                d_tri = [dst_pts[k] for k in tri_idx]
                warp_triangle(ref, warped, s_tri, d_tri)
            canvas = warped

            # Rigid head/ghutra layer on top - see composite_head's comment
            # for why this is a translate-only composite, not part of the
            # mesh warp above.
            composite_head(canvas, target_joints["neck"])

            # Erase the artwork's own (now-misplaced) hand at each target
            # wrist, then draw the real, finger-articulated procedural hand
            # from the MediaPipe hand landmarks for that frame.
            for side, hand_pts in (("left", left_hand_list[i]), ("right", right_hand_list[i])):
                wrist_target = ipt(target_joints[f"{side}_wrist"])
                erase_mask = np.zeros(canvas.shape[:2], dtype=np.uint8)
                cv2.circle(erase_mask, wrist_target, hand_erase_r, 255, -1, cv2.LINE_AA)
                erase_mask = cv2.GaussianBlur(erase_mask, (0, 0), sigmaX=hand_erase_r * 0.15)
                erase_a = (erase_mask.astype(np.float32) / 255.0)[:, :, None]
                sleeve_layer = np.full_like(canvas, SLEEVE_ERASE)
                canvas[:] = (canvas.astype(np.float32) * (1 - erase_a) + sleeve_layer.astype(np.float32) * erase_a).astype(np.uint8)
                if hand_pts is not None:
                    pts, span = normalize_hand(hand_pts)
                    k = hand_target_span / span
                    wrist_px = pts[0]
                    # scale every landmark around the wrist, then place the
                    # (now wrist-relative) hand so its wrist lands exactly
                    # on the target wrist position
                    placed = [(wrist_target[0] + (p[0] - wrist_px[0]) * k,
                               wrist_target[1] + (p[1] - wrist_px[1]) * k) for p in pts]
                    draw_hand(canvas, placed)

        out.write(canvas)
    out.release()

    print(f"Frames with pose: {rendered_with_pose}/{total}", file=sys.stderr)
    print(f"Wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
