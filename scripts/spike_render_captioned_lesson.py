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

ARABIC_FONT = ImageFont.truetype("/System/Library/Fonts/SFArabic.ttf", 30)
LATIN_FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)


def shape_arabic(text):
    return get_display(arabic_reshaper.reshape(text))

sys.path.insert(0, os.path.dirname(__file__))
from spike_cartoon_avatar import (  # noqa: E402
    mp_holistic, extract_pose_px, face_metrics, smooth_series,
    draw_body, draw_face_features, draw_hand, HandTrack, BG, PL,
)

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language"
NORM_DIR = f"{ROOT}/data/zho/spike_mediapipe/lesson/norm"
OUT_DIR = f"{ROOT}/data/zho/spike_mediapipe/lesson/captioned"
DEFAULT_FINAL_OUT_PATH = f"{ROOT}/data/zho/spike_mediapipe/lesson/lesson_captioned_xfade.mp4"
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
    bar_h = 56
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (40, 34, 30), -1)
    cv2.addWeighted(overlay, 0.82, canvas, 0.18, 0, dst=canvas)

    key = (w, h, english, arabic)
    if key not in _CAPTION_CACHE:
        text_layer = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        draw.text((14, bar_h // 2), english, font=LATIN_FONT, fill=(250, 248, 244, 255), anchor="lm")
        shaped = shape_arabic(arabic)
        ar_w = draw.textlength(shaped, font=ARABIC_FONT)
        draw.text((w - 14 - ar_w, bar_h // 2), shaped, font=ARABIC_FONT, fill=(250, 248, 244, 255), anchor="lm")
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
    # addressing the reported shakiness.
    pose_px_list = smooth_series(pose_px_list, alpha=0.18)
    left_pts = smooth_series(left_pts, alpha=0.22)
    right_pts = smooth_series(right_pts, alpha=0.22)
    face_metrics_list = smooth_series(face_metrics_list, alpha=0.18)

    # z export channels, smoothed with the same alphas as their x/y
    # counterparts above - export only, never read by the renderer.
    pose_z_list = smooth_series(pose_z_list, alpha=0.18)
    left_z_export = smooth_series(left_z_export, alpha=0.22)
    right_z_export = smooth_series(right_z_export, alpha=0.22)

    return {"w": w, "h": h, "fps": fps, "pose": pose_px_list, "left": left_pts,
            "right": right_pts, "face": face_metrics_list, "left_z": left_z, "right_z": right_z,
            "pose_z": pose_z_list, "left_z_export": left_z_export, "right_z_export": right_z_export}


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


def render_segment(stem, english, arabic, data, scale_w, out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/{stem}.mp4"
    w, h, fps = data["w"], data["h"], data["fps"]
    pose_px_list, left_pts, right_pts, face_metrics_list = data["pose"], data["left"], data["right"], data["face"]
    left_z, right_z = data["left_z"], data["right_z"]
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
            draw_face_features(canvas, face_c, face_r, face_metrics_list[i])
        l_pts, l_alpha = left_track.get(i, left_pts[i], left_future)
        r_pts, r_alpha = right_track.get(i, right_pts[i], right_future)
        if l_pts:
            draw_hand(canvas, l_pts, l_alpha, zs=left_z[i])
        if r_pts:
            draw_hand(canvas, r_pts, r_alpha, zs=right_z[i])
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
    target_w = max(w for w, h in dims)
    target_h = max(h for w, h in dims)

    filter_parts = []
    for idx in range(len(rendered)):
        w, h = dims[idx]
        if (w, h) == (target_w, target_h):
            filter_parts.append(f"[{idx}:v]setsar=1[n{idx}]")
        else:
            filter_parts.append(
                f"[{idx}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[n{idx}]"
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
    all_shoulder_widths = []
    anchors = {}
    for stem, eng, ar in segments:
        data = detect_segment(stem, norm_dir=norm_dir)
        detected[stem] = data
        all_shoulder_widths += [abs(p["r_sh"][0] - p["l_sh"][0]) for p in data["pose"] if p is not None]
        anchors[stem] = segment_anchor(data["pose"])
        print(f"  detected {stem} ({len(data['pose'])} frames), anchor={anchors[stem]}", file=sys.stderr)

    # One global scale for the whole lesson, not one per segment - fixes
    # "subject keeps changing size."
    global_scale_w = float(np.median(all_shoulder_widths)) if all_shoulder_widths else 100.0
    print(f"Global scale_w = {global_scale_w:.1f} (from {len(all_shoulder_widths)} pooled frames)", file=sys.stderr)

    # One global target position too, not just scale - each segment's real
    # signer stands wherever they happened to stand in their own source
    # video, so without this the character visibly teleports left/right/
    # up/down at every cut, which also makes the crossfades look like
    # glitchy cuts rather than smooth dissolves (blending two different
    # screen positions never looks like a clean transition, no matter the
    # fade duration). Target = median of all segments' own anchors.
    valid_anchors = [a for a in anchors.values() if a is not None]
    target_x = float(np.median([a[0] for a in valid_anchors]))
    target_y = float(np.median([a[1] for a in valid_anchors]))
    print(f"Global target anchor = ({target_x:.1f}, {target_y:.1f})", file=sys.stderr)

    for stem, eng, ar in segments:
        a = anchors[stem]
        if a is None:
            continue
        dx, dy = target_x - a[0], target_y - a[1]
        d = detected[stem]
        d["pose"] = shift_pose_list(d["pose"], dx, dy)
        d["left"] = shift_pts_list(d["left"], dx, dy)
        d["right"] = shift_pts_list(d["right"], dx, dy)
        print(f"  {stem}: shift=({dx:.1f}, {dy:.1f})", file=sys.stderr)

    export_lesson_motion_json(motion_json_path, detected, segments)

    print("=== Pass 2: rendering with shared scale + position ===", file=sys.stderr)
    rendered = []
    for stem, eng, ar in segments:
        path, nframes, fps = render_segment(stem, eng, ar, detected[stem], global_scale_w, out_dir=out_dir)
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
