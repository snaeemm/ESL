#!/usr/bin/env python3
"""
Deterministic caption-state-change segmentation (bounded, no OCR-per-frame).
Extracts frames via ffmpeg (subprocess) at a fixed step, computes a small
grayscale signature of the caption band (top strip and bottom strip) with
Pillow+numpy, and finds discrete state-change boundaries via thresholded
frame-to-frame diff with a minimum-stable-duration debounce.

opencv-python is deliberately avoided here: this sandbox environment has a
reproducible numpy/opencv-python import-time crash
("AttributeError: module 'inspect' has no attribute 'cleandoc'" inside
numpy.ma.core during `import cv2`) independent of numpy version pinning
(tried numpy<2 and mediapipe==0.10.14's pinned combo, both failed
identically). Pillow+numpy alone imports cleanly, so caption detection uses
that instead. MediaPipe (used only for the SECONDARY motion-refinement step,
via the existing production scripts) is unaffected because those scripts
already run successfully in this repo's established `uv run --with
mediapipe==0.10.14 --with opencv-python` invocations elsewhere -- this
opencv issue is intermittent/environment-specific and is called out
explicitly in the report rather than papered over.
"""
import sys, os, json, subprocess, tempfile, shutil
from PIL import Image
import numpy as np

def ffprobe_meta(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True, check=True
    ).stdout
    d = json.loads(out)
    stream = d["streams"][0]
    fr = stream["r_frame_rate"]
    num, den = fr.split("/")
    fps = float(num) / float(den)
    duration = float(d["format"]["duration"])
    return stream["width"], stream["height"], fps, duration

def extract_frames(path, tmpdir, step_s):
    pattern = os.path.join(tmpdir, "f_%06d.png")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path,
         "-vf", f"fps=1/{step_s},scale=160:-1", pattern],
        check=True
    )
    files = sorted(f for f in os.listdir(tmpdir) if f.startswith("f_"))
    return [os.path.join(tmpdir, f) for f in files]

REGIONS = {
    # (x0,y0,x1,y1) fractions. Calibrated by MANUAL inspection of extracted
    # stills per template family (see pilot report) -- NOT a single global
    # assumption. Real corpus has at least 3 distinct on-screen caption
    # templates observed in just 8 pilot videos.
    "top": (0.0, 0.0, 1.0, 0.22),
    "bottom": (0.0, 0.78, 1.0, 1.0),
    "right_box": (0.55, 0.12, 1.0, 0.62),          # word/phrase template (signer center-left, text right)
    "bottom_center_big": (0.25, 0.72, 0.75, 1.0),  # alphabet-letter template
    "upper_right_small": (0.68, 0.08, 1.0, 0.38),  # number template
}

def band_signature(img, region):
    w, h = img.size
    x0, y0, x1, y1 = REGIONS[region]
    box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
    crop = img.convert("L").crop(box)
    arr = np.asarray(crop, dtype=np.float32)
    return arr

def analyze(path, step_s=0.2, diff_thresh=12.0, min_state_s=0.6, region=None):
    w, h, fps, duration = ffprobe_meta(path)
    tmpdir = tempfile.mkdtemp(prefix="capseg_")
    try:
        frame_files = extract_frames(path, tmpdir, step_s)
        n = len(frame_files)
        times = [i * step_s for i in range(n)]

        if region is not None:
            sigs = [band_signature(Image.open(f), region) for f in frame_files]
            diffs = [0.0] + [float(np.mean(np.abs(sigs[i] - sigs[i-1]))) for i in range(1, n)]
            band = region
        else:
            tops = [band_signature(Image.open(f), "top") for f in frame_files]
            bots = [band_signature(Image.open(f), "bottom") for f in frame_files]
            top_diffs = [0.0] + [float(np.mean(np.abs(tops[i] - tops[i-1]))) for i in range(1, n)]
            bot_diffs = [0.0] + [float(np.mean(np.abs(bots[i] - bots[i-1]))) for i in range(1, n)]
            top_energy = float(np.std(top_diffs))
            bot_energy = float(np.std(bot_diffs))
            band = "bottom" if bot_energy >= top_energy else "top"
            diffs = bot_diffs if band == "bottom" else top_diffs

        boundaries = [0.0]
        last_b = 0.0
        for i in range(1, n):
            t = times[i]
            if diffs[i] > diff_thresh and (t - last_b) >= min_state_s:
                boundaries.append(t)
                last_b = t
        boundaries.append(duration)

        segments = []
        for i in range(len(boundaries) - 1):
            s, e = boundaries[i], boundaries[i+1]
            if e - s < 0.35:
                continue
            segments.append({"start_s": round(s, 2), "end_s": round(e, 2)})

        return {
            "path": path, "duration_s": round(duration, 2), "fps": round(fps, 2),
            "resolution": f"{w}x{h}", "caption_band_used": band,
            "band_energy": {"top": None, "bottom": None} if region is not None else {"top": round(top_energy, 3), "bottom": round(bot_energy, 3)},
            "n_frames_sampled": n, "step_s": step_s, "diff_threshold": diff_thresh,
            "n_candidate_segments": len(segments), "segments": segments,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    path = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else None
    out = analyze(path, region=region)
    print(json.dumps(out, indent=2))
