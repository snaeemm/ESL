#!/usr/bin/env python3
"""
SIDE EXPERIMENT. Renders each lesson segment separately through the
procedural avatar with an English+Arabic caption burned in (captions
pulled straight from ZHO's own Arabic-locale labels, so they stay
traceable to the source dictionary, not translated ad hoc), then chains
all segments with real ffmpeg crossfade dissolves instead of hard cuts -
matching the brief's own stated stack ("ffmpeg for trim/crossfade/
concatenation") and smoothing the pose jump at cut points, which is the
whole reason the avatar exists instead of just switching real clips.
"""
import json
import math
import os
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

# Portable font resolution (portability fix): the previous version
# hardcoded macOS-only absolute paths (/System/Library/Fonts/...), which
# would crash immediately on any Linux/Windows host (e.g. CI, another
# developer's machine). Try a prioritized list of common install
# locations per platform, each verified with os.path.isfile before use,
# and fall back to Pillow's built-in default font (always available, no
# file dependency) rather than hardcoding one more absolute path - this
# keeps captions rendering (in *some* readable font) even on a host with
# none of the named fonts installed, instead of hard-crashing the render
# stage entirely.
_ARABIC_FONT_CANDIDATES = [
    "/System/Library/Fonts/SFArabic.ttf",            # macOS
    "/System/Library/Fonts/Supplemental/GeezaPro.ttc",  # macOS (older)
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",  # Linux (Noto)
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",   # Linux (Noto)
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.otf",  # Linux (Noto, opentype)
    "C:/Windows/Fonts/tahoma.ttf",                    # Windows (has Arabic glyphs)
]
_LATIN_FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",            # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux (near-universal)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
    "C:/Windows/Fonts/arial.ttf",                     # Windows
]


def _load_font(candidates, size):
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)  # always available, never crashes the render stage


# Reference canvas height these base sizes were tuned against (matches
# CANONICAL_CANVAS_H below) - draw_caption() scales bar height and font size
# by each segment's OWN h relative to this reference, not a fixed pixel
# count. Segments are rendered onto their own SOURCE clip's native canvas
# (see render_segment/chain_with_xfade), so a fixed-pixel caption baked in
# at e.g. 640x360 would end up visibly bigger than one baked in at 960x540
# once chain_with_xfade scales every segment up to the shared canonical
# canvas - confirmed by the user watching a rendered lesson: captions (and
# the caption bar itself) were noticeably larger/taller on lower-native-
# resolution segments (fingerspelling, some ESL Zayed clips) than on
# 960x540 ZHO segments, even though the FINAL canvas is identical for all.
_CAPTION_REF_H = 540
_BASE_BAR_H = 56
_BASE_ARABIC_SIZE = 30
_BASE_LATIN_SIZE = 26

ARABIC_FONT = _load_font(_ARABIC_FONT_CANDIDATES, _BASE_ARABIC_SIZE)
LATIN_FONT = _load_font(_LATIN_FONT_CANDIDATES, _BASE_LATIN_SIZE)

_SIZED_FONT_CACHE = {}


def _sized_font(kind, size):
    size = max(8, int(round(size)))
    key = (kind, size)
    if key not in _SIZED_FONT_CACHE:
        candidates = _ARABIC_FONT_CANDIDATES if kind == "arabic" else _LATIN_FONT_CANDIDATES
        _SIZED_FONT_CACHE[key] = _load_font(candidates, size)
    return _SIZED_FONT_CACHE[key]


def shape_arabic(text):
    return get_display(arabic_reshaper.reshape(text))


import re as _re
_ARABIC_RANGE = _re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
ARABIC_UNAVAILABLE_MARKER = "[AR UNAVAILABLE]"


def _font_has_arabic_glyphs(font):
    """Verified capability check, not an assumption: render a real Arabic
    test string and confirm it actually produced visible ink (nonzero glyph
    bbox) rather than trusting that a font file 'named Arabic' has coverage,
    and rather than trusting Pillow's load_default() fallback (a bitmap
    Latin-only font) to silently stand in for Arabic."""
    try:
        bbox = font.getbbox(shape_arabic("عربي"))
        return bbox is not None and (bbox[2] - bbox[0]) > 0 and (bbox[3] - bbox[1]) > 0
    except Exception:
        return False


# Verified once at import, not assumed: if the resolved "Arabic" font can't
# actually produce Arabic ink (e.g. every candidate path missing and we fell
# through to Pillow's Latin-only load_default()), fail loudly in the caption
# bar via ARABIC_UNAVAILABLE_MARKER instead of silently emitting tofu boxes.
ARABIC_FONT_CAPABLE = _font_has_arabic_glyphs(ARABIC_FONT)

sys.path.insert(0, os.path.dirname(__file__))
from spike_cartoon_avatar import (  # noqa: E402
    mp_holistic, extract_pose_px, face_metrics, smooth_series,
    draw_body, draw_face_features, draw_hand, HandTrack, BG, PL,
)

# AFTER (richer) renderer integration: reuses the experiment modules under
# experiments/motion_fidelity/ unmodified, wiring their outputs into this
# canonical production render path. Only draw_body / chain_with_xfade stay
# on the original v1 code path - avatar base appearance and the mixed-
# resolution stitch are unchanged.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "experiments", "motion_fidelity"))
from hand_features import palm_orientation  # noqa: E402
from face_features_v2 import (  # noqa: E402
    face_features_v2, compute_brow_calibration, compute_mouth_calibration,
    compute_mouth_contour_calibration, compute_eye_contour_calibration,
)
from head_pose import estimate_head_pose  # noqa: E402
from render_v2 import draw_hand_v3, draw_face_features_v2  # noqa: E402
from one_euro_filter import one_euro_smooth_series  # noqa: E402
from extract_and_render_long import (  # noqa: E402
    _denoise_hand_series, _smooth_face_v2,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORM_DIR = f"{ROOT}/data/zho/spike_mediapipe/lesson/norm"
OUT_DIR = f"{ROOT}/data/zho/spike_mediapipe/lesson/captioned"
DEFAULT_FINAL_OUT_PATH = f"{ROOT}/data/zho/spike_mediapipe/lesson/lesson_captioned_xfade.mp4"
# Fixed final-stitch canvas (see chain_with_xfade) - matches the ZHO source
# clips' native resolution, the majority/institutional source. Every segment
# normalizes to this exact canvas regardless of its own source resolution
# (960x540, 854x480, 640x360, ...), so avatar/caption size is deterministic
# and independent of which sources happen to appear in a given lesson.
CANONICAL_CANVAS_W = 960
CANONICAL_CANVAS_H = 540
# ZHO's native studio fps - see chain_with_xfade's target_fps for why this,
# not max(fps), is used as the final-stitch frame rate.
CANONICAL_CANVAS_FPS = 25
os.makedirs(OUT_DIR, exist_ok=True)
# Cleaned-motion export for the whole lesson (all segments), same idea as
# spike_cartoon_avatar.py's SPIKE_MOTION_JSON but covering every sign, not
# just one clip. Purely a read-only export of data the render pipeline
# already computes - does not feed back into rendering.
LESSON_MOTION_JSON = os.environ.get(
    "SPIKE_LESSON_MOTION_JSON",
    f"{ROOT}/data/zho/spike_mediapipe/lesson/lesson_motion.json",
)

XFADE_DUR = 0.16  # seconds, crossfade at each segment boundary

# (filename stem in norm/, English caption, Arabic caption)
SEGMENTS = [
    ("00_morning", "Morning", "صباح"),
    ("01_science", "Science", "علوم"),
    ("02_class", "Class", "صف دراسي"),
    ("03_teacher", "Teacher", "معلم"),
    ("04_explain", "Explains", "يفسر"),
    ("05_new", "New", "جديد"),
    ("06_important", "Important", "مهم"),
    ("07_class", "Class", "صف دراسي"),
    ("08_examine", "Examine", "يفحص"),
    ("09_cell_kh", "cell (fingerspell)", "خلية (تهجئة)"),
    ("10_cell_l", "cell (fingerspell)", "خلية (تهجئة)"),
    ("11_cell_y", "cell (fingerspell)", "خلية (تهجئة)"),
    ("12_cell_t", "cell (fingerspell)", "خلية (تهجئة)"),
    ("13_class", "Class", "صف دراسي"),
    ("14_looking", "Looks", "ينظر"),
    ("15_inside", "Inside", "داخل"),
    ("16_find", "Find", "يكتشف"),
    ("17_circle", "Circle", "دائرة"),
    ("18_inside", "Inside", "داخل"),
    ("19_center", "Center", "وسط"),
    ("20_important", "Important", "مهم"),
    ("21_nuc_n", "nucleus (fingerspell)", "نواة (تهجئة)"),
    ("22_nuc_w", "nucleus (fingerspell)", "نواة (تهجئة)"),
    ("23_nuc_a", "nucleus (fingerspell)", "نواة (تهجئة)"),
    ("24_nuc_t", "nucleus (fingerspell)", "نواة (تهجئة)"),
    ("25_grows", "Grows", "ينمو"),
    ("26_class", "Class", "صف دراسي"),
    ("27_answer", "Answer", "جواب"),
    ("28_world", "World", "عالم"),
]


_CAPTION_CACHE = {}


def draw_caption(canvas, w, h, english, arabic):
    """Composites an English (left) + properly-shaped Arabic (right)
    caption bar via PIL/SFArabic.ttf, since cv2.putText has no Arabic
    text-shaping (no letter joining, no RTL reordering) and produces
    garbled output for real Arabic script - confirmed by inspection, not
    just a theoretical caveat. arabic_reshaper + python-bidi do the
    shaping/reordering; PIL with a real Arabic-capable font does the
    drawing; only then is it composited back onto the OpenCV canvas."""
    # Resolution-independent sizing (see _CAPTION_REF_H docstring above) -
    # a segment rendered on its own smaller/larger native canvas gets a
    # proportionally smaller/larger bar and font, so once chain_with_xfade
    # scales every segment up to the shared canonical canvas, the caption
    # ends up the SAME absolute size for every segment regardless of which
    # source resolution it was originally detected/rendered at.
    scale = h / _CAPTION_REF_H
    bar_h = max(20, int(round(_BASE_BAR_H * scale)))
    ar_size = _BASE_ARABIC_SIZE * scale
    lat_size = _BASE_LATIN_SIZE * scale
    pad = max(6, int(round(14 * scale)))

    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (40, 34, 30), -1)
    cv2.addWeighted(overlay, 0.82, canvas, 0.18, 0, dst=canvas)

    key = (w, h, english, arabic)
    if key not in _CAPTION_CACHE:
        lat_font = _sized_font("latin", lat_size)
        text_layer = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        draw.text((pad, bar_h // 2), english, font=lat_font, fill=(250, 248, 244, 255), anchor="lm")
        # Never blindly shape+draw whatever "arabic" string arrived: only do
        # so if it's both real Arabic script AND the resolved font can
        # actually render Arabic glyphs. Otherwise show an explicit
        # unavailable marker (Latin font, always renders) rather than
        # silently producing tofu boxes or fabricating text.
        if ARABIC_FONT_CAPABLE and arabic and _ARABIC_RANGE.search(arabic):
            shaped = shape_arabic(arabic)
            ar_font = _sized_font("arabic", ar_size)
        else:
            shaped = ARABIC_UNAVAILABLE_MARKER
            ar_font = lat_font
        ar_w = draw.textlength(shaped, font=ar_font)
        draw.text((w - pad - ar_w, bar_h // 2), shaped, font=ar_font, fill=(250, 248, 244, 255), anchor="lm")
        _CAPTION_CACHE[key] = np.array(text_layer)

    layer_rgba = _CAPTION_CACHE[key]
    region = canvas[h - bar_h:h, 0:w]
    alpha = layer_rgba[:, :, 3:4].astype(np.float32) / 255.0
    region[:] = (region.astype(np.float32) * (1 - alpha) + layer_rgba[:, :, :3].astype(np.float32) * alpha).astype(np.uint8)


def detect_segment(stem, norm_dir=NORM_DIR):
    """Detection only - no rendering, no scale decision yet. Splitting
    this out is what makes a single GLOBAL scale possible: every segment
    is a separate short clip, so a scale computed per-segment (as the
    single-continuous-video renderer does) locks onto a different value
    per segment - the real underlying signers/framing aren't identical -
    and the character visibly jumps size at every cut. The fix is to
    detect everything first, then pick one scale from the combined pool
    before any segment is rendered."""
    clip = f"{norm_dir}/{stem}.mp4"
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    pose_px_list, left_pts, right_pts, face_metrics_list = [], [], [], []
    left_z, right_z = [], []
    # Raw (x,y,z) per hand landmark, and raw face landmarks - needed by the
    # AFTER renderer (palm_orientation, estimate_head_pose, face_features_v2)
    # which all require data beyond what face_metrics()/x,y-only hand points
    # carry. Collected alongside the existing v1 channels, which are left
    # untouched.
    left_xyz, right_xyz, face_lm_list = [], [], []
    # pose_z_list / hand_z_export: collected purely for the motion-data
    # export below. left_z/right_z above are the pre-existing halo inputs
    # (raw, unsmoothed, read by render_segment) and are untouched; these
    # are separate copies so the export can smooth its own z data without
    # altering halo rendering.
    pose_z_list, left_z_export, right_z_export = [], [], []
    with mp_holistic.Holistic(static_image_mode=False, model_complexity=1,
                               min_detection_confidence=0.5, min_tracking_confidence=0.5,
                               refine_face_landmarks=False) as holistic:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            r = holistic.process(rgb)
            pose_px_list.append(extract_pose_px(r.pose_landmarks.landmark, w, h) if r.pose_landmarks else None)
            left_pts.append([(lm.x * w, lm.y * h) for lm in r.left_hand_landmarks.landmark]
                             if r.left_hand_landmarks else None)
            right_pts.append([(lm.x * w, lm.y * h) for lm in r.right_hand_landmarks.landmark]
                              if r.right_hand_landmarks else None)
            left_xyz.append([(lm.x * w, lm.y * h, lm.z) for lm in r.left_hand_landmarks.landmark]
                             if r.left_hand_landmarks else None)
            right_xyz.append([(lm.x * w, lm.y * h, lm.z) for lm in r.right_hand_landmarks.landmark]
                              if r.right_hand_landmarks else None)
            face_lm_list.append(list(r.face_landmarks.landmark) if r.face_landmarks else None)
            # z: depth relative to the wrist (more negative = closer to
            # camera), used only for the hand halo - not smoothed since it
            # only drives a coarse "how forward is the hand" halo size.
            left_z.append([lm.z for lm in r.left_hand_landmarks.landmark]
                           if r.left_hand_landmarks else None)
            right_z.append([lm.z for lm in r.right_hand_landmarks.landmark]
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
            left_z_export.append([lm.z for lm in r.left_hand_landmarks.landmark]
                                  if r.left_hand_landmarks else None)
            right_z_export.append([lm.z for lm in r.right_hand_landmarks.landmark]
                                   if r.right_hand_landmarks else None)
            face_metrics_list.append(face_metrics(r.face_landmarks.landmark, w, h) if r.face_landmarks else None)
    cap.release()

    # Stronger smoothing than the earlier single-clip renderer (0.25 -> 0.18)
    # - more history weight, less raw-frame noise passed through, directly
    # addressing the reported shakiness. Pose and face v1 stay on the
    # existing fixed-alpha EMA (matching experiments/motion_fidelity's own
    # extract_and_render_long.py, which also keeps pose/face_v1 on
    # prod_smooth and reserves one_euro for hands only).
    pose_px_list = smooth_series(pose_px_list, alpha=0.18)
    face_metrics_list = smooth_series(face_metrics_list, alpha=0.18)

    # Hands: denoise short spurious blip detections first (same order as
    # extract_and_render_long.py - denoising before smoothing prevents the
    # smoother from treating a blip as a real short run), then replace the
    # fixed-alpha EMA with the adaptive One-Euro filter on the raw (x,y,z)
    # series - this is the AFTER renderer's hand channel, used both for
    # (x,y) point drawing and for z (palm-orientation / depth shading).
    left_xyz = _denoise_hand_series(left_xyz)
    right_xyz = _denoise_hand_series(right_xyz)
    left_xyz = one_euro_smooth_series(left_xyz, fps)
    right_xyz = one_euro_smooth_series(right_xyz, fps)
    left_pts = [[(x, y) for x, y, z in pts] if pts is not None else None for pts in left_xyz]
    right_pts = [[(x, y) for x, y, z in pts] if pts is not None else None for pts in right_xyz]
    left_z = [[z for x, y, z in pts] if pts is not None else None for pts in left_xyz]
    right_z = [[z for x, y, z in pts] if pts is not None else None for pts in right_xyz]

    # Face v2 (independent L/R brow/eye/mouth + raw landmarks for head pose):
    # computed per-frame from the raw landmarks, then EMA-smoothed the same
    # way extract_and_render_long.py's _smooth_face_v2 does (recursively,
    # blink/eye-state kept as a discrete current-frame value, not smeared).
    face_v2_raw = [face_features_v2(lm, w, h) if lm is not None else None for lm in face_lm_list]
    face_v2_list = _smooth_face_v2(face_v2_raw, alpha=0.18)

    # z export channels, smoothed with the same alphas as their x/y
    # counterparts above - export only, never read by the renderer.
    pose_z_list = smooth_series(pose_z_list, alpha=0.18)
    left_z_export = smooth_series(left_z_export, alpha=0.22)
    right_z_export = smooth_series(right_z_export, alpha=0.22)

    return {"w": w, "h": h, "fps": fps, "pose": pose_px_list, "left": left_pts,
            "right": right_pts, "face": face_metrics_list, "left_z": left_z, "right_z": right_z,
            "pose_z": pose_z_list, "left_z_export": left_z_export, "right_z_export": right_z_export,
            "left_xyz": left_xyz, "right_xyz": right_xyz,
            "face_lm": face_lm_list, "face_v2": face_v2_list}


def segment_anchor(pose_px_list):
    """Median neck (mid-shoulder) position across a segment's frames -
    where this segment's character is 'centered' on screen."""
    xs, ys = [], []
    for p in pose_px_list:
        if p is None:
            continue
        xs.append((p["l_sh"][0] + p["r_sh"][0]) / 2)
        ys.append((p["l_sh"][1] + p["r_sh"][1]) / 2)
    if not xs:
        return None
    return (float(np.median(xs)), float(np.median(ys)))


def shift_pose_list(pose_px_list, dx, dy):
    out = []
    for p in pose_px_list:
        if p is None:
            out.append(None)
            continue
        out.append({k: (v[0] + dx, v[1] + dy) for k, v in p.items()})
    return out


def shift_pts_list(pts_list, dx, dy):
    out = []
    for pts in pts_list:
        if pts is None:
            out.append(None)
            continue
        out.append([(x + dx, y + dy) for x, y in pts])
    return out


def rescale_and_shift_pose_list(pose_px_list, anchor, target_x, target_y, ratio):
    """Fix for the mixed-resolution/mixed-framing avatar scale bug: the
    OLD shift_pose_list() above only ever TRANSLATES a segment's raw
    detected skeleton - it never rescales the actual bone lengths/span
    (shoulder-to-shoulder, arm reach, torso height). draw_body() draws
    the torso/limb SPAN directly from these raw positions (only their
    stroke THICKNESS is separately sized via scale_w), so a segment whose
    real-world signer occupies a different fraction of its own native
    frame (whether from a different source resolution or genuinely
    closer/wider camera framing - confirmed real via a rendered ESL Zayed
    clip: same fixed anchor target, but the whole skeleton span was still
    the clip's own larger raw size, pushing the head/hands past the
    canvas edges) came out the wrong SIZE entirely, not just
    mispositioned.

    This scales every landmark's offset from its OWN segment's detected
    anchor by `ratio` (= this lesson's global target physical scale /
    this segment's own detected physical scale, both already resolution-
    normalized by the caller - see render_lesson()), THEN recenters on
    the global target anchor position - a single geometric operation
    (scale-around-a-point, then translate) that replaces the old shift-
    only approach and is what actually normalizes each segment's whole
    body to the lesson's shared physical scale, not just its stroke
    thickness or its center point."""
    ax, ay = anchor
    out = []
    for p in pose_px_list:
        if p is None:
            out.append(None)
            continue
        out.append({
            k: (target_x + (v[0] - ax) * ratio, target_y + (v[1] - ay) * ratio)
            for k, v in p.items()
        })
    return out


def rescale_and_shift_pts_list(pts_list, anchor, target_x, target_y, ratio):
    """Hand-landmark counterpart of rescale_and_shift_pose_list() above -
    same scale-around-anchor-then-translate operation, so hands stay
    correctly sized/positioned relative to the now-correctly-scaled body
    instead of at their old (wrong) raw scale."""
    ax, ay = anchor
    out = []
    for pts in pts_list:
        if pts is None:
            out.append(None)
            continue
        out.append([(target_x + (x - ax) * ratio, target_y + (y - ay) * ratio) for x, y in pts])
    return out


_POSE_KEYS = ("l_sh", "r_sh", "l_el", "r_el", "l_wr", "r_wr", "l_hip", "r_hip")


def export_lesson_motion_json(path, detected, segments):
    """Writes one JSON covering every lesson segment's cleaned (smoothed,
    globally scale/position-aligned) motion data - the same per-frame data
    render_segment() is about to draw from, just exported instead of/as
    well as rendered. Read-only w.r.t. the pipeline: called after the
    global shift is applied and before any rendering happens, doesn't
    change anything main() or render_segment() do.

    Note: segments are still stitched together with a crossfade dissolve
    in the final lesson_captioned_xfade.mp4, so this file's frame indices
    are per-segment (each segment restarts at frame 0), not a single
    frame-accurate timeline of the crossfaded output."""
    out_segments = []
    for stem, english, arabic in segments:
        d = detected[stem]
        total = len(d["pose"])
        frames = []
        for i in range(total):
            pose_px, pose_z = d["pose"][i], d["pose_z"][i]
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
                "left_hand": hand_json(d["left"][i], d["left_z_export"][i]),
                "right_hand": hand_json(d["right"][i], d["right_z_export"][i]),
                "face": d["face"][i],
            })
        out_segments.append({
            "stem": stem, "english": english, "arabic": arabic,
            "fps": d["fps"], "width": d["w"], "height": d["h"],
            "frames": frames,
        })

    with open(path, "w") as f:
        json.dump({"segments": out_segments}, f)
    n = sum(len(s["frames"]) for s in out_segments)
    print(f"Wrote lesson motion data ({len(out_segments)} segments, {n} frames total) -> {path}",
          file=sys.stderr)


def render_segment(stem, english, arabic, data, scale_w, out_dir=OUT_DIR,
                    brow_calibration=None, mouth_calibration=None,
                    mouth_contour_calibration=None, eye_contour_calibration=None):
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/{stem}.mp4"
    w, h, fps = data["w"], data["h"], data["fps"]
    pose_px_list, left_pts, right_pts, face_metrics_list = data["pose"], data["left"], data["right"], data["face"]
    left_z, right_z = data["left_z"], data["right_z"]
    left_xyz, right_xyz = data["left_xyz"], data["right_xyz"]
    face_lm_list, face_v2_list = data["face_lm"], data["face_v2"]
    total = len(pose_px_list)

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
    out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    for i in range(total):
        canvas = np.full((h, w, 3), BG, dtype=np.uint8)
        if pose_px_list[i] is not None:
            face_c, face_r = draw_body(canvas, pose_px_list[i], w, h, scale_w=scale_w)
            # AFTER renderer: draw_face_features_v2 needs raw face landmarks
            # (for head-pose roll) alongside the v2 metrics; fall back to the
            # v1 renderer for any frame with no face detection at all (same
            # gating extract_and_render_long.py uses).
            if face_lm_list[i] is not None:
                head_pose = estimate_head_pose(face_lm_list[i], w, h)
                draw_face_features_v2(canvas, face_c, face_r, face_metrics_list[i], face_v2_list[i],
                                       head_pose, brow_calibration, mouth_calibration,
                                       mouth_contour_calibration, eye_contour_calibration)
            else:
                draw_face_features(canvas, face_c, face_r, face_metrics_list[i])
        l_pts, l_alpha = left_track.get(i, left_pts[i], left_future)
        r_pts, r_alpha = right_track.get(i, right_pts[i], right_future)
        if l_pts:
            nz = palm_orientation(left_xyz[i], handedness="left")["normal"][2] if left_xyz[i] else None
            draw_hand_v3(canvas, l_pts, l_alpha, left_z[i], nz)
        if r_pts:
            nz = palm_orientation(right_xyz[i], handedness="right")["normal"][2] if right_xyz[i] else None
            draw_hand_v3(canvas, r_pts, r_alpha, right_z[i], nz)
        draw_caption(canvas, w, h, english, arabic)
        out.write(canvas)
    out.release()
    print(f"{stem}: {total} frames -> {out_path}", file=sys.stderr)
    return out_path, total, fps


def _probe_wh(path):
    cap = cv2.VideoCapture(path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return w, h


def chain_with_xfade(rendered, final_out_path=DEFAULT_FINAL_OUT_PATH):
    """Builds a single ffmpeg filter_complex chaining sequential xfade
    transitions across all segments - each transition overlaps the tail
    of one clip with the head of the next rather than hard-cutting.

    render_segment() draws each segment's procedural avatar onto a canvas
    sized to match that segment's own SOURCE clip resolution (norm_dir/),
    so segments detected from a downloaded ZHO sign clip and segments
    detected from the (differently-sized) fingerspelling alphabet clips
    can legitimately come out at different pixel dimensions - `xfade`
    requires every input to match exactly. Rather than touching detection/
    scale/anchor/motion logic (which operates in each segment's own native
    pixel space) or the source clips themselves, every rendered segment is
    normalized here, at the output/stitching boundary only: scaled down
    to fit a shared target canvas while preserving aspect ratio, then
    letterboxed (padded) to fill it exactly - never stretched/distorted.
    Target canvas = the largest width/height actually seen across this
    lesson's rendered segments, so the higher-resolution (typically real
    ZHO sign) segments are never downscaled and the lower-resolution
    (fingerspelling) segments are only padded, not blown up and blurred."""
    inputs = []
    for path, _, _ in rendered:
        inputs += ["-i", path]

    dims = [_probe_wh(path) for path, _, _ in rendered]
    # Canonical FIXED output canvas (build order Step: cross-source visual
    # canonicalization) - deliberately NOT max(dims). A per-run "largest
    # segment wins" target made final canvas size depend on which segments
    # happened to appear together in a given lesson: a lesson mixing ZHO
    # (960x540) with an ESL Zayed source at a different native resolution/
    # aspect ratio than this run's tester happened to hit would silently
    # letterbox-pad the mismatched segment smaller within the frame, so the
    # avatar/captions visibly differ in size/scale depending on YouTube
    # source resolution (360p/480p/540p/720p/...). A fixed canonical target
    # means every segment - ZHO, ESL Zayed, fingerspell, any future source -
    # always normalizes to the exact same output canvas, independent of
    # what happens to be in this particular lesson.
    target_w, target_h = CANONICAL_CANVAS_W, CANONICAL_CANVAS_H
    # xfade requires every input to share one timebase too, not just one
    # resolution - render_segment() writes each segment at its own SOURCE
    # clip's native fps (cv2 CAP_PROP_FPS), so a ZHO clip (e.g. 25fps) next
    # to a differently-sourced clip (e.g. an ESL Zayed download at 30fps)
    # hits "input link main timebase does not match ... xfade timebase"
    # and ffmpeg drops the whole filter graph. Normalized here at the same
    # stitching boundary as the resolution fix above, not in detection/
    # render_segment (which must stay in each segment's own native fps for
    # correct motion timing).
    #
    # Deliberately NOT max(fps) (was the original approach): ffmpeg's `fps`
    # filter converts by nearest-frame sampling, which means the filter
    # duplicates frames when upsampling and drops frames when downsampling.
    # max() picks whichever source happens to have the highest native fps
    # in THIS lesson's particular mix - almost always an ESL Zayed clip
    # (YouTube's 30000/1001 standard) rather than ZHO's 25fps studio
    # recordings. Since ZHO is the majority/institutional source in most
    # lessons, that meant the MAJORITY of segments got upsampled (25->30),
    # i.e. duplicate-framed, while the minority ESL Zayed segments passed
    # through untouched - measured directly on a rendered final_episode.mp4
    # (job 013fbd2aa3f0): a ZHO segment (FATHER) showed near-zero
    # frame-to-frame pixel diff (a frozen/duplicated frame) on 15 of 50
    # consecutive frame-pairs (~30%), vs only 2 of 41 (~5%) on an ESL Zayed
    # segment (BROTHER) in the same video - the opposite of "ESL Zayed looks
    # choppier" (a live user report), which was actually majority-ZHO
    # judder from this exact upsampling. Fixed to the same canonical-source
    # rationale as CANONICAL_CANVAS_W/H above: match ZHO's native fps, so
    # the majority source passes through untouched and only the minority
    # (typically ESL Zayed) source gets converted - and downsampling drops
    # frames rather than duplicating them, which reads as smoother motion
    # than periodic freezing for the same conversion ratio.
    target_fps = CANONICAL_CANVAS_FPS

    filter_parts = []
    for idx in range(len(rendered)):
        w, h = dims[idx]
        if (w, h) == (target_w, target_h):
            filter_parts.append(f"[{idx}:v]fps={target_fps},setsar=1[n{idx}]")
        else:
            # Pad color matches the avatar's own background (BG in
            # spike_cartoon_avatar.py, BGR (240,246,250) -> hex FAF6F0),
            # not black. A source clip with a non-16:9 native aspect ratio
            # (e.g. an ESL Zayed 640x480/4:3 download next to every other
            # clip's 16:9) genuinely needs letterbox/pillarbox padding here
            # to reach the canonical canvas without distorting the avatar's
            # proportions - that size difference is an honest tradeoff, not
            # a bug. But black bars read as a jarring "this segment is
            # broken/different" discontinuity against every other segment's
            # shared cream background (live user report: "the lesson video
            # becomes small and completely different than the entire other
            # thing" on the ESL Zayed "I" sign, which is exactly this
            # 640x480 clip) - matching the pad color to BG makes the size
            # difference far less visually jarring even though it doesn't
            # (and shouldn't) eliminate it.
            filter_parts.append(
                f"[{idx}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=0xFAF6F0,fps={target_fps},setsar=1[n{idx}]"
            )

    prev_label = "n0"
    cum_duration = rendered[0][1] / rendered[0][2]
    for idx in range(1, len(rendered)):
        path, nframes, fps = rendered[idx]
        dur = nframes / fps
        offset = cum_duration - XFADE_DUR
        out_label = f"v{idx}"
        filter_parts.append(
            f"[{prev_label}][n{idx}]xfade=transition=fade:duration={XFADE_DUR}:offset={offset:.3f}[{out_label}]"
        )
        prev_label = out_label
        cum_duration = offset + dur

    filter_complex = ";".join(filter_parts)
    os.makedirs(os.path.dirname(final_out_path), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
        final_out_path,
    ]
    subprocess.run(cmd, check=True)
    print(f"Wrote {final_out_path}", file=sys.stderr)
    return final_out_path


def render_lesson(segments=None, norm_dir=NORM_DIR, out_dir=OUT_DIR,
                   motion_json_path=LESSON_MOTION_JSON, final_out_path=DEFAULT_FINAL_OUT_PATH):
    """Additive entry point (build order Step 14): accepts a generated
    segment manifest instead of relying only on the hard-coded module-level
    SEGMENTS list, so run_pipeline.py can drive this renderer from a
    validated sign sequence. Calling with no arguments reproduces exactly
    the original behavior/paths (the known-working lesson_captioned_xfade.mp4)
    unchanged — this is what `python spike_render_captioned_lesson.py` still
    does via main() below.

    segments: list of (stem, english_caption, arabic_caption) tuples, same
    shape as the original module-level SEGMENTS constant.
    """
    if segments is None:
        segments = SEGMENTS

    print("=== Pass 1: detecting all segments ===", file=sys.stderr)
    detected = {}
    all_shoulder_widths_norm = []
    segment_scale_norm = {}
    anchors = {}
    anchors_norm = {}
    for stem, eng, ar in segments:
        data = detect_segment(stem, norm_dir=norm_dir)
        detected[stem] = data
        # Resolution-invariant scale/anchor fix: render_segment() draws
        # each segment onto a canvas sized to that segment's OWN source
        # resolution (data["w"]/data["h"] - see chain_with_xfade's
        # docstring, this is a deliberate design choice preserved here,
        # NOT the bug). The bug was pooling/applying RAW absolute-pixel
        # shoulder widths and anchor positions across segments whose
        # native resolutions can differ substantially (e.g. a 1280x720
        # ESL Zayed source clip next to 640x360 ZHO clips - confirmed via
        # a real rendered lesson: the higher-resolution segment's avatar
        # came out oversized and cropped past the frame edges, because a
        # scale/shift computed mostly from smaller-canvas segments was
        # applied as literal absolute pixels onto a much larger canvas).
        # Fix: normalize every raw pixel quantity by ITS OWN segment's
        # frame width/height into a resolution-independent fraction
        # BEFORE pooling into the one global scale/anchor (same pooled-
        # median architecture as before, now scale-invariant), then
        # convert back to each segment's own absolute pixels when
        # applying it below - never touches detect_segment/render_segment
        # themselves or the deliberate per-segment native-canvas design.
        w, h = data["w"], data["h"]
        this_seg_widths_norm = [abs(p["r_sh"][0] - p["l_sh"][0]) / w for p in data["pose"] if p is not None]
        all_shoulder_widths_norm += this_seg_widths_norm
        # Per-segment own normalized scale (median shoulder width as a
        # fraction of ITS OWN frame width) - needed below to compute how
        # much to rescale THIS segment's whole skeleton to match the
        # lesson-wide global target scale, not just how much to shift it.
        segment_scale_norm[stem] = float(np.median(this_seg_widths_norm)) if this_seg_widths_norm else None
        a = segment_anchor(data["pose"])
        anchors[stem] = a
        anchors_norm[stem] = (a[0] / w, a[1] / h) if a is not None else None
        print(f"  detected {stem} ({len(data['pose'])} frames), anchor={a}, wh=({w},{h}), "
              f"own_scale_norm={segment_scale_norm[stem]}", file=sys.stderr)

    # One global scale for the whole lesson, not one per segment - fixes
    # "subject keeps changing size." Now computed in resolution-
    # independent fractional units (fraction of that segment's own frame
    # width), so it means the same thing ("this fraction of the frame is
    # shoulder-width") regardless of any one segment's native resolution.
    global_scale_w_norm = float(np.median(all_shoulder_widths_norm)) if all_shoulder_widths_norm else 0.15
    print(f"Global scale_w (fraction of frame width) = {global_scale_w_norm:.4f} "
          f"(from {len(all_shoulder_widths_norm)} pooled frames)", file=sys.stderr)

    # One global target position too, not just scale - each segment's real
    # signer stands wherever they happened to stand in their own source
    # video, so without this the character visibly teleports left/right/
    # up/down at every cut, which also makes the crossfades look like
    # glitchy cuts rather than smooth dissolves (blending two different
    # screen positions never looks like a clean transition, no matter the
    # fade duration). Target = median of all segments' own anchors, also
    # in resolution-independent fractional units for the same reason.
    valid_anchors_norm = [a for a in anchors_norm.values() if a is not None]
    target_x_norm = float(np.median([a[0] for a in valid_anchors_norm]))
    target_y_norm = float(np.median([a[1] for a in valid_anchors_norm]))
    print(f"Global target anchor (fraction of frame) = ({target_x_norm:.4f}, {target_y_norm:.4f})", file=sys.stderr)

    for stem, eng, ar in segments:
        a = anchors[stem]
        if a is None:
            continue
        d = detected[stem]
        w, h = d["w"], d["h"]
        # Denormalize back to THIS segment's own absolute pixels before
        # computing the shift, so a segment at any resolution ends up
        # with its signer at the same RELATIVE on-screen position as
        # every other segment, not the same absolute pixel offset.
        target_x_px, target_y_px = target_x_norm * w, target_y_norm * h
        # The actual scale fix: rescale this segment's whole skeleton
        # (not just shift its position) so its physical size, as a
        # fraction of ITS OWN frame, matches the lesson-wide global
        # target - this is what a same-string absolute-pixel shift alone
        # could never do, and is what was missing before (see
        # rescale_and_shift_pose_list's docstring for the full story).
        # ratio > 1 means this segment's own signer occupies LESS of
        # their frame than the lesson target (needs enlarging); ratio < 1
        # means they occupy MORE (needs shrinking, exactly the ESL Zayed
        # SCHOOL STARTS/LOSE FOCUS case that was rendering oversized).
        own_scale = segment_scale_norm.get(stem)
        ratio = (global_scale_w_norm / own_scale) if own_scale else 1.0
        d["pose"] = rescale_and_shift_pose_list(d["pose"], a, target_x_px, target_y_px, ratio)
        d["left"] = rescale_and_shift_pts_list(d["left"], a, target_x_px, target_y_px, ratio)
        d["right"] = rescale_and_shift_pts_list(d["right"], a, target_x_px, target_y_px, ratio)
        # Post-rescale jitter damping: rescale_and_shift_pts_list() is a
        # pure per-frame linear transform (scale-around-anchor, same ratio
        # every frame) of hand points that were already one-euro-smoothed
        # in detect_segment() - it can't inject NEW noise, but it does
        # multiply whatever residual smoothing noise was left by `ratio`,
        # so a segment needing real enlargement (ratio > 1, e.g. a
        # fingerspelling clip filmed wide so the signer's hand occupies a
        # small fraction of its own frame) comes out of this loop with
        # visibly jerkier hands than before the rescale existed, even
        # though nothing about the ORIGINAL smoothing changed. Measured on
        # a real rendered lesson (job bdff1892c9da) via its own exported
        # motion.json: mean frame-to-frame hand displacement, normalized
        # by shoulder width, rose from 0.026 pre-rescale-fix to 0.040
        # post-rescale-fix (+56%), correlating with segments that needed
        # the largest ratio. A light second EMA pass here (alpha=0.25,
        # tuned by replaying that same motion.json offline against a
        # target of matching the pre-fix jitter level) brings it back to
        # ~0.028 without touching the actual target size/position the P0
        # fix computed - a pure temporal smoothing pass changes frame-to-
        # frame variance, not the sequence's mean position.
        d["left"] = smooth_series(d["left"], alpha=0.25)
        d["right"] = smooth_series(d["right"], alpha=0.25)
        print(f"  {stem}: own_scale={own_scale}, ratio={ratio:.3f}, target_px=({target_x_px:.1f}, {target_y_px:.1f})",
              file=sys.stderr)

    export_lesson_motion_json(motion_json_path, detected, segments)

    # Face v2 calibration (brow/mouth-corner/mouth-contour/eye-contour),
    # pooled across ALL lesson segments before rendering starts - same
    # global-pool pattern as global_scale_w/target anchor above, and the
    # same pattern experiments/motion_fidelity/extract_and_render_long.py
    # actually uses (one calibration computed over its whole 9-clip pool,
    # not recomputed separately per clip): a per-segment-only calibration
    # would be unstable for the fingerspelling segments, which are only a
    # couple of seconds each.
    all_v2 = []
    for stem, eng, ar in segments:
        all_v2 += [v2 for v2 in detected[stem]["face_v2"] if v2 is not None]
    brow_calibration = compute_brow_calibration(all_v2)
    mouth_calibration = compute_mouth_calibration(all_v2)
    mouth_contour_calibration = compute_mouth_contour_calibration(all_v2)
    eye_contour_calibration = compute_eye_contour_calibration(all_v2)
    print(f"Face v2 calibration pooled from {len(all_v2)} frames "
          f"(brow={brow_calibration is not None}, mouth={mouth_calibration is not None})", file=sys.stderr)

    print("=== Pass 2: rendering with shared scale + position ===", file=sys.stderr)
    rendered = []
    for stem, eng, ar in segments:
        d = detected[stem]
        # Denormalize the resolution-independent global scale fraction
        # back to THIS segment's own absolute pixels - a segment at any
        # native resolution ends up drawing its avatar at the same
        # RELATIVE size (fraction of its own frame width) as every other
        # segment, instead of one fixed absolute-pixel size that only
        # looks right for segments near the pooled dominant resolution.
        scale_w_px = global_scale_w_norm * d["w"]
        path, nframes, fps = render_segment(
            stem, eng, ar, d, scale_w_px, out_dir=out_dir,
            brow_calibration=brow_calibration, mouth_calibration=mouth_calibration,
            mouth_contour_calibration=mouth_contour_calibration,
            eye_contour_calibration=eye_contour_calibration)
        rendered.append((path, nframes, fps))
    return chain_with_xfade(rendered, final_out_path=final_out_path)


def main():
    """Unchanged entry point: reproduces the original, known-working
    behavior exactly (module-level SEGMENTS, original paths) - this is
    what makes lesson_captioned_xfade.mp4 still regenerable byte-for-byte
    the same way it always was."""
    render_lesson()


if __name__ == "__main__":
    main()
