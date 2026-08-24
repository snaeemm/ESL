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

# ESL Zayed supplementary-source clip prep (mirrors the ZHO cache layout
# above, keyed by supplementary_id / youtube_video_id instead of ZHO
# catalog id). Raw downloads are cached per SOURCE VIDEO (one YouTube video
# can back multiple WORD records at different timestamps), the trimmed
# segment is cached per supplementary_id, matching the "raw download cache
# + trim cache keyed by id + norm_cache" design used for ZHO. This reuses
# the exact download+trim approach manually proven in commit bb3895f
# (yt-dlp fetch of the full source video, then ffmpeg -ss/-to trim to the
# catalog record's segment_start_s/segment_end_s) rather than reinventing it.
ESL_ZAYED_RAW_DIR = os.path.join(ROOT, "data", "zho", "spike_mediapipe", "esl_zayed_raw")
ESL_ZAYED_NORM_DIR = os.path.join(ROOT, "data", "zho", "spike_mediapipe", "esl_zayed_clips")


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


# --------------------------------------------------------------------------
# ESL Zayed supplementary-source clip materialization.
# --------------------------------------------------------------------------

def _esl_zayed_raw_path(youtube_video_id: str) -> str:
    return os.path.join(ESL_ZAYED_RAW_DIR, f"{youtube_video_id}.mp4")


def _ensure_esl_zayed_downloaded(youtube_video_id: str, source_url: str) -> str:
    """Downloads the full ESL Zayed source video (yt-dlp), cached per
    youtube_video_id so multiple WORD records backed by the same video are
    never re-downloaded. Mirrors the ZHO _ensure_downloaded()'s cache-then-
    fetch shape, reusing the exact yt-dlp approach manually proven in
    bb3895f rather than a different implementation."""
    dest = _esl_zayed_raw_path(youtube_video_id)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    import shutil as _shutil
    yt_dlp = _shutil.which("yt-dlp")
    if not yt_dlp:
        raise ClipPrepError("yt-dlp is not on PATH (required to download ESL Zayed source video)")
    cmd = [
        yt_dlp, "-f", "mp4/best[ext=mp4]/best", "-o", dest,
        "--no-playlist", "--quiet", "--no-warnings", source_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0 or not os.path.exists(dest) or os.path.getsize(dest) == 0:
        raise ClipPrepError(
            f"yt-dlp failed to download ESL Zayed source video {youtube_video_id} ({source_url}): "
            f"{result.stderr.strip()[:500]}"
        )
    return dest


def prepare_esl_zayed_clip(supplementary_ref: dict) -> dict:
    """Downloads (if needed, cached by youtube_video_id) the full ESL
    Zayed source video and trims it (cached by supplementary_id) to the
    catalog record's own segment_start_s/segment_end_s — this is a KNOWN
    interval from the catalog, unlike ZHO's MediaPipe-detected active
    window, so no active-window detection subprocess is needed here.
    Raises ClipPrepError on any failure; callers must not silently
    substitute or omit the item on failure (fail closed)."""
    supplementary_id = supplementary_ref.get("supplementary_id")
    youtube_video_id = supplementary_ref.get("youtube_video_id")
    source_url = supplementary_ref.get("source_url") or (
        f"https://www.youtube.com/watch?v={youtube_video_id}" if youtube_video_id else None)
    start_s = supplementary_ref.get("segment_start_s")
    end_s = supplementary_ref.get("segment_end_s")
    if not supplementary_id or not youtube_video_id or not source_url or start_s is None or end_s is None:
        raise ClipPrepError(
            f"ESL Zayed supplementary_ref missing required provenance fields "
            f"(supplementary_id/youtube_video_id/source_url/segment_start_s/segment_end_s): {supplementary_ref!r}"
        )
    raw_path = _ensure_esl_zayed_downloaded(youtube_video_id, source_url)
    norm_path = os.path.join(ESL_ZAYED_NORM_DIR, f"{supplementary_id}.mp4")
    _ffmpeg_trim(raw_path, norm_path, float(start_s), float(end_s))
    if not os.path.exists(norm_path) or os.path.getsize(norm_path) == 0:
        raise ClipPrepError(f"ESL Zayed trim produced no output for {supplementary_id} (source={youtube_video_id})")
    return {
        "supplementary_id": supplementary_id,
        "youtube_video_id": youtube_video_id,
        "source_url": source_url,
        "arabic_text": supplementary_ref.get("arabic_text"),
        "english_meaning": supplementary_ref.get("english_meaning"),
        "raw_clip_path": raw_path,
        "norm_clip_path": norm_path,
        "trim_window_s": [float(start_s), float(end_s)],
    }
