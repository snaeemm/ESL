"""In-memory job manager + per-job worker thread.

No Redis/Celery — a prototype-appropriate thread pool is enough here: job
generation is I/O/subprocess-bound (Ollama HTTP calls, ffmpeg, MediaPipe
subprocesses), not CPU-bound in this process, and only one demo job runs
at a time in practice. Each job gets its own output directory
(outputs/webapp_jobs/<job_id>/) and a JSON event log the frontend polls
via GET /api/jobs/{id}/events — this IS the pipeline's own stage events
from lib/pipeline_runner.py.run(), not a separate progress simulation.
"""
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field

import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.pipeline_runner import run as run_pipeline, PipelineBlocked
from lib.understand import DEFAULT_MODEL

JOBS_DIR = os.path.join(ROOT, "outputs", "webapp_jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9_.-]+")


def sanitize_filename(name: str) -> str:
    """Strips anything that isn't alnum/underscore/dot/dash — used for
    every user-supplied filename before it ever touches the filesystem.
    No path separators can survive this."""
    name = os.path.basename(name)
    name = _SAFE_FILENAME.sub("_", name)
    return name or "source"


@dataclass
class Job:
    job_id: str
    status: str = "queued"  # queued | running | done | blocked | error
    created_at: float = field(default_factory=time.time)
    output_dir: str = ""
    events: list = field(default_factory=list)
    error: str = ""
    params: dict = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_event(self, event: dict):
        with self.lock:
            self.events.append(event)
            with open(os.path.join(self.output_dir, "events.json"), "w", encoding="utf-8") as f:
                json.dump(self.events, f, indent=2, ensure_ascii=False)

    def snapshot(self):
        with self.lock:
            return {
                "job_id": self.job_id, "status": self.status, "created_at": self.created_at,
                "error": self.error, "params": self.params, "num_events": len(self.events),
                "last_event": self.events[-1] if self.events else None,
            }


_JOBS: dict[str, Job] = {}
_JOBS_LOCK = threading.Lock()


def create_job(source_path: str, source_language: str, target_duration: int,
               model: str, review_mode: str) -> Job:
    job_id = uuid.uuid4().hex[:12]
    output_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)

    job = Job(job_id=job_id, output_dir=output_dir, params={
        "source_language": source_language, "target_duration": target_duration,
        "model": model, "review_mode": review_mode,
    })
    with _JOBS_LOCK:
        _JOBS[job_id] = job

    allow_review_render = (review_mode == "PROTOTYPE")

    def worker():
        job.status = "running"
        try:
            for event in run_pipeline(
                source_path=source_path, output_dir=output_dir, source_language=source_language,
                target_duration=target_duration, model=model or DEFAULT_MODEL,
                allow_review_render=allow_review_render, skip_clip_prep=False,
            ):
                job.add_event(event)
        except PipelineBlocked as e:
            job.status = "blocked"
            job.error = str(e)
            return
        except Exception as e:  # noqa: BLE001 — last-resort catch so a job never hangs "running" forever
            job.status = "error"
            job.error = f"{type(e).__name__}: {e}"
            job.add_event({"stage": "ERROR", "status": "error", "message": job.error, "data": {}})
            return
        job.status = "done"

    threading.Thread(target=worker, daemon=True).start()
    return job


def get_job(job_id: str) -> Job | None:
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def list_jobs() -> list[Job]:
    with _JOBS_LOCK:
        return sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)


def load_job_from_disk_if_missing(job_id: str) -> Job | None:
    """Recovers a job's read-only state from its output dir + events.json
    after a backend restart (in-memory _JOBS is otherwise lost) — history
    view (build order Step 22) stays usable across restarts without a
    database."""
    output_dir = os.path.join(JOBS_DIR, job_id)
    events_path = os.path.join(output_dir, "events.json")
    if not os.path.isdir(output_dir) or not os.path.isfile(events_path):
        return None
    with open(events_path, encoding="utf-8") as f:
        events = json.load(f)
    status = "done"
    if events and events[-1]["status"] == "blocked":
        status = "blocked"
    elif events and events[-1]["stage"] != "DONE":
        status = "error"  # process died mid-run before a restart
    job = Job(job_id=job_id, status=status, output_dir=output_dir, events=events)
    with _JOBS_LOCK:
        _JOBS[job_id] = job
    return job
