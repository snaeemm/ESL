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

# Blocker E (caption-boundary dead time): the OCR caption-alignment pilot
# already produced PER-ITEM card timestamps (caption_start_s/caption_end_s)
# for many ESL Zayed source videos, tighter than the coarser
# segment_start_s/segment_end_s baked into the main supplementary catalog
# (e.g. some catalog rows span an entire multi-item source video because
# their materialization pass didn't do fine per-word alignment - see
# ESL_ZAYED_0016's own notes field: "Full duration sampled at 4 timestamps
# ... single teaching item confirmed"). Reusing this EXISTING alignment
# data (not generating new dataset processing) lets the caption-card
# boundary itself cap the trim window, closing the gap hand-presence-only
# trimming can't: a signer's hands staying active across a caption
# transition (e.g. into the NEXT word's card) no longer survives into the
# clip, because the window is capped at this item's own caption_end_s
# before hand-detection is even run.
ESL_ZAYED_OCR_ALIGNMENT_DIR = os.path.join(
    ROOT, "data", "zho", "spike_mediapipe", "esl_zayed_caption_pilot_v2_20260823")
_OCR_CAPTION_BUFFER_S = 0.5  # small pad so we don't clip the sign itself flush against the card edge


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

    window = _run_active_window_detector(clip_path)
    if window is None:
        raise ClipPrepError(f"spike_find_active_window.py failed/found no hand for {clip_path}")
    start_s, end_s = window

    cache[catalog_id] = {"start_s": start_s, "end_s": end_s, "clip_path": clip_path}
    _save_trim_cache(cache)
    return start_s, end_s


def _lookup_ocr_caption_window(youtube_video_id: str, english_meaning: str, arabic_text: str) -> tuple:
    """Looks up this item's own caption-card window from the existing OCR
    alignment pilot data (data/zho/spike_mediapipe/esl_zayed_caption_pilot_v2_20260823/
    scale_result_<video_id>.json), matched by english_meaning or
    arabic_text. Returns (caption_start_s, caption_end_s) with a small
    buffer applied, or None if no alignment file exists for this video or
    no item matches - callers must treat None as "no tighter bound
    available", never as an error (this is a refinement, not a
    requirement - the catalog's own segment_start_s/segment_end_s remains
    the fail-closed source of truth when this lookup can't help)."""
    path = os.path.join(ESL_ZAYED_OCR_ALIGNMENT_DIR, f"scale_result_{youtube_video_id}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    for item in data.get("items", []):
        item_en = (item.get("english_meaning_from_video") or "").strip().lower()
        item_ar = (item.get("arabic_caption") or "").strip()
        if (english_meaning and item_en == english_meaning.strip().lower()) or (arabic_text and item_ar == arabic_text.strip()):
            c_start, c_end = item.get("caption_start_s"), item.get("caption_end_s")
            if c_start is None or c_end is None or c_end <= c_start:
                return None
            return max(0.0, c_start - _OCR_CAPTION_BUFFER_S), c_end + _OCR_CAPTION_BUFFER_S
    return None


def _run_active_window_detector(clip_path: str) -> tuple:
    """Runs scripts/spike_find_active_window.py (MediaPipe hand-detection
    dead-time trim) against clip_path and returns (start_s, end_s) relative
    to clip_path itself, or None if detection failed/found no hand at all
    (e.g. a short or noisy clip) - callers must treat None as "keep the
    untrimmed clip", never as an error that drops the item."""
    cmd = [
        "uv", "run", "--python", "3.11",
        "--with", "mediapipe==0.10.14", "--with", "opencv-python", "--with", "numpy",
        "python3", os.path.join(ROOT, "scripts", "spike_find_active_window.py"), clip_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        start_s, end_s = (float(x) for x in result.stdout.strip().split())
    except (ValueError, IndexError):
        return None
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
    catalog record's own segment_start_s/segment_end_s — this is a KNOWN,
    caption-verified interval from the catalog, unlike ZHO's raw downloaded
    clip which needs MediaPipe active-window detection just to find where
    the sign is at all.

    Blocker E fix: that caption-verified interval can still include
    "dead time" at its edges — the signer entering/leaving frame, an idle
    hand fragment, a caption transition frame — that ZHO's per-clip
    MediaPipe dead-time trim (spike_find_active_window.py, via
    _compute_trim_window/prepare_clip above) already screens out but this
    path previously skipped entirely (see FINAL_REPORT.md's "no MediaPipe
    dead-time trim" / "stray hand/finger shape" / "scale-position
    difference" findings). Fix: reuse the SAME detector, run against the
    already caption-trimmed clip (not the raw video) so refinement can only
    ever narrow the window — it is mathematically bounded inside
    [segment_start_s, segment_end_s] by construction, never outside the
    caption-verified interval. If detection finds no hand at all (e.g. a
    very short clip), the caption-verified trim is kept unchanged rather
    than treating that as an error - conservative, fail-open on refinement
    only, never fail-open on the clip existing at all.
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
    start_s, end_s = float(start_s), float(end_s)
    raw_path = _ensure_esl_zayed_downloaded(youtube_video_id, source_url)
    norm_path = os.path.join(ESL_ZAYED_NORM_DIR, f"{supplementary_id}.mp4")
    caption_verified_window = [start_s, end_s]
    dead_time_trim_applied = False
    caption_boundary_capped = False

    if os.path.exists(norm_path) and os.path.getsize(norm_path) > 0:
        # Already materialized (and, if a refinement pass has run before,
        # already refined) in a prior run - cache hit, nothing to redo.
        cache = _load_trim_cache()
        cached = cache.get(f"ESL_ZAYED::{supplementary_id}")
        if cached:
            caption_verified_window = [cached["caption_start_s"], cached["caption_end_s"]]
            dead_time_trim_applied = cached.get("dead_time_trim_applied", False)
            caption_boundary_capped = cached.get("caption_boundary_capped", False)
    else:
        # Caption-boundary cap: if the OCR alignment pilot has a tighter,
        # per-item card window for this exact video+word (see
        # _lookup_ocr_caption_window's docstring above), intersect it with
        # the catalog's own segment_start_s/segment_end_s BEFORE trimming.
        # This is a cap, never an expansion - max()/min() below can only
        # narrow [start_s, end_s], so it stays inside the catalog's own
        # caption-verified interval even when the OCR window is imprecise.
        # This is what closes the gap hand-presence-only trimming can't:
        # a signer's hands staying active across a caption-card transition
        # (e.g. drifting into the NEXT word's card) is now excluded by the
        # card boundary itself, before hand-detection even runs.
        ocr_window = _lookup_ocr_caption_window(
            youtube_video_id, supplementary_ref.get("english_meaning"), supplementary_ref.get("arabic_text"))
        trim_start, trim_end = start_s, end_s
        if ocr_window is not None:
            ocr_start, ocr_end = ocr_window
            capped_start = max(start_s, ocr_start)
            capped_end = min(end_s, ocr_end)
            if capped_end > capped_start:
                trim_start, trim_end = capped_start, capped_end
                caption_boundary_capped = (trim_start, trim_end) != (start_s, end_s)

        _ffmpeg_trim(raw_path, norm_path, trim_start, trim_end)
        if not os.path.exists(norm_path) or os.path.getsize(norm_path) == 0:
            raise ClipPrepError(f"ESL Zayed trim produced no output for {supplementary_id} (source={youtube_video_id})")

        # Dead-time refinement: run the SAME detector ZHO uses, against the
        # already caption-trimmed (and now possibly caption-boundary-capped)
        # clip. Any window it returns is relative to that clip (0..duration),
        # so re-applying it can only shrink the window further - it can
        # never move the boundary outside [trim_start, trim_end], which is
        # itself already inside [start_s, end_s].
        refined = _run_active_window_detector(norm_path)
        if refined is not None:
            r_start, r_end = refined
            if r_end > r_start:
                refined_path = norm_path + ".refined.mp4"
                _ffmpeg_trim(norm_path, refined_path, r_start, r_end)
                if os.path.exists(refined_path) and os.path.getsize(refined_path) > 0:
                    os.replace(refined_path, norm_path)
                    dead_time_trim_applied = True

        cache = _load_trim_cache()
        cache[f"ESL_ZAYED::{supplementary_id}"] = {
            "caption_start_s": start_s, "caption_end_s": end_s,
            "dead_time_trim_applied": dead_time_trim_applied,
            "caption_boundary_capped": caption_boundary_capped, "clip_path": norm_path,
        }
        _save_trim_cache(cache)

    return {
        "supplementary_id": supplementary_id,
        "youtube_video_id": youtube_video_id,
        "source_url": source_url,
        "arabic_text": supplementary_ref.get("arabic_text"),
        "english_meaning": supplementary_ref.get("english_meaning"),
        "raw_clip_path": raw_path,
        "norm_clip_path": norm_path,
        "trim_window_s": caption_verified_window,
        "dead_time_trim_applied": dead_time_trim_applied,
        "caption_boundary_capped": caption_boundary_capped,
    }
