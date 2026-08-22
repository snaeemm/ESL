"""Thin FastAPI wrapper around the existing pipeline (lib/pipeline_runner.py).

No business logic lives here — this module only: validates/saves user
input into an isolated job directory, starts a background job, and
exposes read-only views over the SAME JSON artifacts run_pipeline.py
already produces. It never shells out with user-controlled strings, never
exposes arbitrary filesystem paths, and never returns .env/secrets.
"""
import json
import os
import shutil
import subprocess
import sys

from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.jobs import create_job, get_job, list_jobs, load_job_from_disk_if_missing, sanitize_filename, JOBS_DIR
from lib.understand import DEFAULT_MODEL

app = FastAPI(title="MoE Sign Language Episode Generator — Backend (prototype)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ALLOWED_UPLOAD_EXTENSIONS = (".txt", ".md")
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2MB — an academic source passage, not a file drop

# Only these exact filenames may ever be downloaded — no path traversal,
# no arbitrary repository browsing (Step 21/24).
DOWNLOADABLE_ARTIFACTS = {
    "final_episode.mp4", "traceability.json", "traceability.md",
    "validation.json", "review_required.md", "episode.json",
    "understanding.json", "source_manifest.json", "stage_timings.json",
}


def _job_or_404(job_id: str):
    job = get_job(job_id) or load_job_from_disk_if_missing(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


def _read_json_if_exists(path: str):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


@app.get("/api/environment")
def environment_status():
    """Powers the frontend's failure states (Step 23) BEFORE a job is even
    created — Ollama unavailable, model missing, ffmpeg missing."""
    from lib.pipeline_runner import check_environment
    problems = check_environment(DEFAULT_MODEL)
    return {"ok": not problems, "problems": problems, "model": DEFAULT_MODEL}


@app.post("/api/jobs")
async def create_job_endpoint(
    source_text: str = Form(default=None),
    source_file: UploadFile = File(default=None),
    source_language: str = Form(default="auto"),
    target_duration: int = Form(default=45),
    review_mode: str = Form(default="STRICT"),
    model: str = Form(default=None),
):
    if review_mode not in ("STRICT", "PROTOTYPE"):
        raise HTTPException(400, "review_mode must be STRICT or PROTOTYPE")
    if source_language not in ("auto", "en", "ar"):
        raise HTTPException(400, "source_language must be auto, en, or ar")
    if not (10 <= target_duration <= 180):
        raise HTTPException(400, "target_duration must be between 10 and 180 seconds")

    if not source_text and not source_file:
        raise HTTPException(400, "Provide either source_text or source_file")

    # Save the source into an ISOLATED job-scoped directory before anything
    # else runs — never the shared repo content/ tree, and never trusted
    # as a path from the client.
    import uuid
    staging_id = uuid.uuid4().hex[:12]
    staging_dir = os.path.join(JOBS_DIR, f"_staging_{staging_id}")
    os.makedirs(staging_dir, exist_ok=True)

    if source_file is not None:
        filename = sanitize_filename(source_file.filename or "source.txt")
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type '{ext}'. Only .txt and .md are accepted.")
        content = await source_file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, "File too large (max 2MB for a lesson source passage).")
        source_path = os.path.join(staging_dir, filename)
        with open(source_path, "wb") as f:
            f.write(content)
    else:
        if len(source_text.encode("utf-8")) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, "Pasted text too large (max 2MB).")
        source_path = os.path.join(staging_dir, "pasted_source.md")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_text)

    job = create_job(
        source_path=source_path, source_language=source_language,
        target_duration=target_duration, model=model or DEFAULT_MODEL, review_mode=review_mode,
    )
    return {"job_id": job.job_id, "status": job.status}


@app.get("/api/jobs")
def list_jobs_endpoint():
    """History view (Step 22) — reads job directories on disk too, not
    just in-memory jobs from this process's lifetime."""
    seen = {j.job_id: j for j in list_jobs()}
    if os.path.isdir(JOBS_DIR):
        for name in os.listdir(JOBS_DIR):
            if name.startswith("_staging_") or name in seen:
                continue
            job = load_job_from_disk_if_missing(name)
            if job:
                seen[name] = job
    rows = []
    for job in sorted(seen.values(), key=lambda j: j.created_at, reverse=True)[:50]:
        manifest = _read_json_if_exists(os.path.join(job.output_dir, "source_manifest.json")) or {}
        validation = _read_json_if_exists(os.path.join(job.output_dir, "validation.json")) or {}
        dp = validation.get("duration_plan", {})
        cov = validation.get("checks", {}).get("coverage", {})
        rows.append({
            "job_id": job.job_id, "status": job.status,
            "created_at": job.created_at, "source_path": manifest.get("source_path"),
            "source_language": manifest.get("source_language"),
            "requested_duration_s": dp.get("requested_duration_s"),
            "actual_duration_s": dp.get("actual_duration_s"),
            "validation_status": validation.get("overall_status"),
            "verified_lexical_sign_coverage_pct": cov.get("verified_lexical_sign_coverage_pct"),
        })
    return rows


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return _job_or_404(job_id).snapshot()


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str):
    job = _job_or_404(job_id)
    events = job.events
    if not events:
        events_path = os.path.join(job.output_dir, "events.json")
        events = _read_json_if_exists(events_path) or []
    return events


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str):
    job = _job_or_404(job_id)
    d = job.output_dir
    manifest = _read_json_if_exists(os.path.join(d, "source_manifest.json"))
    understanding = _read_json_if_exists(os.path.join(d, "understanding.json"))
    episode = _read_json_if_exists(os.path.join(d, "episode.json"))
    validation = _read_json_if_exists(os.path.join(d, "validation.json"))
    timings = _read_json_if_exists(os.path.join(d, "stage_timings.json"))
    has_video = os.path.isfile(os.path.join(d, "final_episode.mp4"))
    return {
        "job_id": job_id, "status": job.status, "error": job.error,
        "source_manifest": manifest, "understanding_summary": {
            "model": understanding["model"] if understanding else None,
            "num_concepts_extracted": understanding["num_concepts_extracted"] if understanding else None,
            "num_verified": sum(1 for c in understanding["concepts"] if c.get("source_span_verified")) if understanding else None,
        } if understanding else None,
        "episode": episode, "validation": validation, "stage_timings": timings,
        "has_video": has_video,
    }


@app.get("/api/jobs/{job_id}/video")
def job_video(job_id: str):
    job = _job_or_404(job_id)
    path = os.path.join(job.output_dir, "final_episode.mp4")
    if not os.path.isfile(path):
        raise HTTPException(404, "video not yet available for this job")
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/jobs/{job_id}/traceability")
def job_traceability(job_id: str):
    job = _job_or_404(job_id)
    trace = _read_json_if_exists(os.path.join(job.output_dir, "traceability.json"))
    if trace is None:
        raise HTTPException(404, "traceability not yet available for this job")
    return trace


@app.get("/api/jobs/{job_id}/review")
def job_review(job_id: str):
    job = _job_or_404(job_id)
    validation = _read_json_if_exists(os.path.join(job.output_dir, "validation.json"))
    review_md_path = os.path.join(job.output_dir, "review_required.md")
    review_md = None
    if os.path.isfile(review_md_path):
        with open(review_md_path, encoding="utf-8") as f:
            review_md = f.read()
    episode = _read_json_if_exists(os.path.join(job.output_dir, "episode.json"))
    return {"validation": validation, "review_markdown": review_md, "episode": episode}


@app.get("/api/jobs/{job_id}/artifacts")
def job_artifacts(job_id: str):
    job = _job_or_404(job_id)
    rows = []
    for name in sorted(DOWNLOADABLE_ARTIFACTS):
        path = os.path.join(job.output_dir, name)
        if os.path.isfile(path):
            rows.append({"name": name, "size_bytes": os.path.getsize(path)})
    return rows


@app.get("/api/jobs/{job_id}/artifacts/{name}")
def job_artifact_download(job_id: str, name: str):
    if name not in DOWNLOADABLE_ARTIFACTS:
        raise HTTPException(404, "artifact not found")
    job = _job_or_404(job_id)
    path = os.path.join(job.output_dir, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "artifact not found")
    return FileResponse(path, filename=name)
