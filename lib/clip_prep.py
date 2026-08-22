"""CLIP PREPARATION (build order Step 12).

Closes the gap identified in the audit: nothing previously turned a
catalog entry into a downloadable, trimmed, "norm"-ready clip
automatically — the existing lesson/norm/*.mp4 clips were assembled by
hand. This module reuses, rather than reimplements:

  - scripts/zho_download.py's `download()` + `slugify()` for fetching the
    raw ZHO clip (same URL scheme, same on-disk layout under data/zho/clips/).
  - scripts/spike_find_active_window.py's hand-detection trim-window logic,
    invoked as a subprocess exactly as its own docstring documents
    (`uv run --python 3.11 --with "mediapipe==0.10.14" ...`), rather than
    re-implementing MediaPipe hand-detection here.

Caches both the raw download and the computed trim window keyed by
catalog id, so the same sign is never downloaded or re-trimmed twice
across runs.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from zho_download import download, slugify  # noqa: E402  (reused, not duplicated)

CLIPS_DIR = os.path.join(ROOT, "data", "zho", "clips")
TRIM_CACHE_PATH = os.path.join(ROOT, "data", "zho", "spike_mediapipe", "trim_cache.json")
NORM_CACHE_DIR = os.path.join(ROOT, "data", "zho", "spike_mediapipe", "norm_cache")


class ClipPrepError(RuntimeError):
    pass


def _load_trim_cache() -> dict:
    if os.path.isfile(TRIM_CACHE_PATH):
        with open(TRIM_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_trim_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(TRIM_CACHE_PATH), exist_ok=True)
    with open(TRIM_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def _raw_clip_path(catalog_ref: dict) -> str:
    slug = slugify(catalog_ref["word_en"])
    id8 = catalog_ref["id"][:8]
    return os.path.join(CLIPS_DIR, catalog_ref["category"], f"{slug}_{id8}.mp4")


def _ensure_downloaded(catalog_ref: dict) -> str:
    dest = _raw_clip_path(catalog_ref)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    ok = download(catalog_ref["video_url"], dest)
    if not ok:
        raise ClipPrepError(f"Failed to download clip for catalog id {catalog_ref['id']} ({catalog_ref['word_en']})")
    return dest


def _compute_trim_window(clip_path: str, catalog_id: str) -> tuple:
    cache = _load_trim_cache()
    if catalog_id in cache:
        c = cache[catalog_id]
        return c["start_s"], c["end_s"]

    cmd = [
        "uv", "run", "--python", "3.11",
        "--with", "mediapipe==0.10.14", "--with", "opencv-python", "--with", "numpy",
        "python3", os.path.join(ROOT, "scripts", "spike_find_active_window.py"), clip_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ClipPrepError(
            f"spike_find_active_window.py failed for {clip_path}: {result.stderr.strip()}"
        )
    start_s, end_s = (float(x) for x in result.stdout.strip().split())

    cache[catalog_id] = {"start_s": start_s, "end_s": end_s, "clip_path": clip_path}
    _save_trim_cache(cache)
    return start_s, end_s


def _ffmpeg_trim(src: str, dest: str, start_s: float, end_s: float) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", src, "-ss", f"{start_s:.2f}", "-to", f"{end_s:.2f}",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-an", dest,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ClipPrepError(f"ffmpeg trim failed for {src}: {result.stderr.strip()}")


def prepare_clip(catalog_ref: dict) -> dict:
    """Downloads (if needed), auto-trims (if needed, cached), and returns
    a provenance dict: {catalog_id, word_en, category, raw_clip_path,
    norm_clip_path, trim_window_s}. Raises ClipPrepError on any failure —
    callers must not silently substitute a different clip on failure."""
    raw_path = _ensure_downloaded(catalog_ref)
    start_s, end_s = _compute_trim_window(raw_path, catalog_ref["id"])
    norm_path = os.path.join(NORM_CACHE_DIR, f"{catalog_ref['id']}.mp4")
    _ffmpeg_trim(raw_path, norm_path, start_s, end_s)
    return {
        "catalog_id": catalog_ref["id"],
        "word_en": catalog_ref["word_en"],
        "category": catalog_ref["category"],
        "raw_clip_path": raw_path,
        "norm_clip_path": norm_path,
        "trim_window_s": [start_s, end_s],
    }
