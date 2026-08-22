"""Shared pipeline execution — the SINGLE place SOURCE -> ... -> TRACEABILITY
actually runs. Both `run_pipeline.py` (CLI) and `webapp/backend` (the FastAPI
job worker) call `run()` below rather than each having their own copy of the
stage logic, per the requirement that the web app must wrap the existing
pipeline, not duplicate its business logic.

`run()` is a generator: each `yield` is one stage-progress event, consumed
by the CLI (printed to stderr) or the backend (written to a per-job event
log the frontend polls). Nothing in this module talks to a UI directly —
it has no knowledge that a web app exists.
"""
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lib.source_loader import load_source, write_source_manifest
from lib.understand import extract_concepts, DEFAULT_MODEL, UnderstandError
from lib.episode_builder import build_episode
from lib.sign_plan import build_sign_plans
from lib.sign_resolver import resolve_units
from lib.duration_planner import plan_episode_duration
from lib.validator import validate_episode, write_review_markdown, can_render, STATUS_BLOCKED
from lib.clip_prep import prepare_clip, ClipPrepError
from lib.traceability import build_traceability, write_traceability_json, write_traceability_markdown

STAGES = ["ENVIRONMENT_CHECK", "SOURCE", "UNDERSTAND", "STRUCTURE", "SIGN_PLAN",
          "SIGN_RESOLUTION", "DURATION_PLANNING", "VALIDATE", "CLIP_PREP",
          "RENDER", "TRACEABILITY", "DONE"]


class PipelineBlocked(RuntimeError):
    """Raised (and always the LAST thing yielded, as a status='blocked'
    event) when the pipeline cannot proceed — bad environment, model
    unreachable, or VALIDATE says BLOCKED/REVIEW_REQUIRED-without-flag."""


def probe_duration_s(video_path: str):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return round(float(r.stdout.strip()), 2)
    except Exception:
        return None


def check_environment(model: str) -> list:
    problems = []
    if not shutil.which("ffmpeg"):
        problems.append("ffmpeg is not on PATH (required for final video assembly).")
    if not shutil.which("uv"):
        problems.append("uv is not on PATH (required for MediaPipe clip preparation subprocess).")
    if not shutil.which("ollama"):
        problems.append("ollama is not on PATH (required for the local UNDERSTAND/STRUCTURE stages).")
    else:
        try:
            r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
            if model not in r.stdout:
                problems.append(f"Model '{model}' is not pulled in Ollama. Run: ollama pull {model}")
        except Exception as e:
            problems.append(f"Could not query `ollama list`: {e}")
    return problems


def _event(stage, status, message, data=None, t0=None):
    e = {"stage": stage, "status": status, "message": message, "data": data or {},
         "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if t0 is not None:
        e["elapsed_s"] = round(time.time() - t0, 2)
    return e


def run(source_path: str, output_dir: str, source_language: str = "auto",
        target_duration: int = 45, model: str = DEFAULT_MODEL,
        allow_review_render: bool = False, skip_clip_prep: bool = False):
    """Generator: yields one event dict per stage transition. Writes every
    artifact listed in README's Outputs section into output_dir. Raises
    PipelineBlocked (after yielding a final status='blocked' event) if the
    pipeline cannot complete — callers should stop consuming and surface
    the last event's message, never a raw traceback, to an end user."""
    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()
    stage_timings = {}

    def timed(stage_name):
        stage_timings[stage_name] = round(time.time() - t0, 2)

    yield _event("ENVIRONMENT_CHECK", "running", "Checking local environment (Ollama, model, ffmpeg, uv)...", t0=t0)
    problems = check_environment(model)
    if problems:
        yield _event("ENVIRONMENT_CHECK", "blocked", "; ".join(problems), {"problems": problems}, t0=t0)
        raise PipelineBlocked("; ".join(problems))
    timed("ENVIRONMENT_CHECK")
    yield _event("ENVIRONMENT_CHECK", "done", "Environment OK.", t0=t0)

    # --- SOURCE ---------------------------------------------------------
    yield _event("SOURCE", "running", "Verifying academic source...", t0=t0)
    manifest = load_source(source_path, language=source_language)
    write_source_manifest(manifest, os.path.join(output_dir, "source_manifest.json"))
    timed("SOURCE")
    yield _event("SOURCE", "done", "Source verified and hashed.", {
        "source_id": manifest["source_id"], "source_language": manifest["source_language"],
        "source_language_mode": manifest["source_language_mode"],
    }, t0=t0)

    # --- UNDERSTAND -------------------------------------------------------
    yield _event("UNDERSTAND", "running", f"Extracting grounded concepts with {model}...", t0=t0)
    try:
        understanding = extract_concepts(manifest["source_text"], model=model)
    except UnderstandError as e:
        yield _event("UNDERSTAND", "blocked", str(e), t0=t0)
        raise PipelineBlocked(str(e))
    with open(os.path.join(output_dir, "understanding.json"), "w", encoding="utf-8") as f:
        json.dump(understanding, f, indent=2, ensure_ascii=False)
    n_verified = sum(1 for c in understanding["concepts"] if c.get("source_span_verified"))
    timed("UNDERSTAND")
    yield _event("UNDERSTAND", "done",
                  f"{understanding['num_concepts_extracted']} concepts extracted, {n_verified} with verified source spans.",
                  {"num_concepts_extracted": understanding["num_concepts_extracted"], "num_verified": n_verified,
                   "json_parsed_successfully": understanding["json_parsed_successfully"]}, t0=t0)

    # --- STRUCTURE --------------------------------------------------------
    yield _event("STRUCTURE", "running", "Building educational episode...", t0=t0)
    episode = build_episode(understanding["concepts"], model=model, target_duration_s=target_duration)
    units = episode["units"]
    timed("STRUCTURE")
    yield _event("STRUCTURE", "done", f"{len(units)} educational units structured.",
                  {"num_units": len(units)}, t0=t0)

    # --- SIGN PLAN ----------------------------------------------------------
    yield _event("SIGN_PLAN", "running", "Creating semantic sign plan...", t0=t0)
    units = build_sign_plans(units, model=model)
    n_plan_ok = sum(1 for u in units if u.get("semantic_plan_status") == "OK")
    n_plan_items = sum(len(u.get("semantic_sign_plan", [])) for u in units)
    timed("SIGN_PLAN")
    yield _event("SIGN_PLAN", "done", f"{n_plan_items} semantic units planned across {n_plan_ok}/{len(units)} educational units.",
                  {"num_semantic_items": n_plan_items, "units_planned_ok": n_plan_ok}, t0=t0)

    # --- SIGN RESOLUTION (+ TERMINOLOGY) ------------------------------------
    yield _event("SIGN_RESOLUTION", "running", "Resolving semantic units against UAE/ZHO sign assets; preparing Arabic fingerspelling fallback...", t0=t0)
    units = resolve_units(units, source_language=manifest["source_language"], model=model)
    timed("SIGN_RESOLUTION")
    yield _event("SIGN_RESOLUTION", "done", "Sign resolution complete.", {}, t0=t0)

    # --- DURATION PLANNING --------------------------------------------------
    yield _event("DURATION_PLANNING", "running", "Selecting a coherent episode subset that fits the requested duration...", t0=t0)
    duration_plan = plan_episode_duration(units, target_duration_s=target_duration)
    units = duration_plan["units"]
    included_units = [u for u in units if u["included_in_episode"]]
    with open(os.path.join(output_dir, "episode.json"), "w", encoding="utf-8") as f:
        json.dump({"source_id": manifest["source_id"], "source_path": manifest["source_path"],
                   "duration_plan_summary": {k: v for k, v in duration_plan.items() if k != "units"},
                   "units": units}, f, indent=2, ensure_ascii=False)
    timed("DURATION_PLANNING")
    yield _event("DURATION_PLANNING", "done",
                  f"{duration_plan['units_included']} units included (~{duration_plan['estimated_duration_s']:.0f}s estimated), "
                  f"{duration_plan['units_dropped']} dropped to fit the {target_duration}s target.",
                  {k: v for k, v in duration_plan.items() if k != "units"}, t0=t0)

    # --- VALIDATE -------------------------------------------------------------
    yield _event("VALIDATE", "running", "Validating provenance and review requirements...", t0=t0)
    validation = validate_episode(included_units, manifest["source_text"])
    validation["duration_plan"] = {k: v for k, v in duration_plan.items() if k != "units"}
    with open(os.path.join(output_dir, "validation.json"), "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, ensure_ascii=False)
    write_review_markdown(units, validation, os.path.join(output_dir, "review_required.md"))
    cov = validation["checks"]["coverage"]
    timed("VALIDATE")
    yield _event("VALIDATE", "done", f"Validation status: {validation['overall_status']}.", {
        "overall_status": validation["overall_status"],
        "verified_lexical_sign_coverage_pct": cov["verified_lexical_sign_coverage_pct"],
        "renderable_coverage_with_fallback_pct": cov["renderable_coverage_with_fallback_pct"],
        "review_required_units": cov["review_required_units"],
        "unsupported_units": cov["unsupported_units"],
    }, t0=t0)

    if not can_render(validation, allow_review_render):
        reason = ("critical provenance failures" if validation["overall_status"] == STATUS_BLOCKED
                   else "expert review is required (strict review mode)")
        yield _event("VALIDATE", "blocked", f"Stopping before rendering: {reason}.",
                      {"overall_status": validation["overall_status"]}, t0=t0)
        raise PipelineBlocked(reason)

    if skip_clip_prep:
        yield _event("DONE", "done", "Stopped after VALIDATE (skip_clip_prep set).", {}, t0=t0)
        return

    # --- CLIP PREP ------------------------------------------------------------
    yield _event("CLIP_PREP", "running", "Preparing sign clips (downloading + auto-trimming, cached)...", t0=t0)
    motion_dir = os.path.join(output_dir, "motion", "norm")
    os.makedirs(motion_dir, exist_ok=True)
    segments, seg_trace, clip_prep_failures = [], [], []
    seg_idx = 0
    for u in included_units:
        for r_idx, r in enumerate(u.get("sign_resolution", [])):
            catalog_refs = []
            if r["status"] == "VERIFIED_SIGN" and r.get("catalog_ref"):
                catalog_refs = [(r["catalog_ref"], r["term"])]
            elif r["status"] == "FINGERSPELL_CANDIDATE" and r.get("fingerspell"):
                catalog_refs = [(cr["catalog_row"], cr["name_ar"]) for cr in r["fingerspell"]["catalog_refs"] if cr.get("catalog_row")]
            else:
                continue
            for cref, label in catalog_refs:
                stem = f"{seg_idx:03d}_{label}"
                try:
                    prep = prepare_clip(cref)
                except ClipPrepError as e:
                    clip_prep_failures.append({"term": r["term"], "catalog_id": cref.get("id") or cref.get("catalog_id"), "error": str(e)})
                    continue
                dest = os.path.join(motion_dir, f"{stem}.mp4")
                shutil.copyfile(prep["norm_clip_path"], dest)
                segments.append((stem, r["term"], r.get("terminology", {}).get("arabic_term") or r["term"]))
                seg_trace.append({"stem": stem, "unit_id": u["unit_id"], "resolution_index": r_idx})
                seg_idx += 1
    timed("CLIP_PREP")
    yield _event("CLIP_PREP", "done", f"{len(segments)} clip segments prepared ({len(clip_prep_failures)} failures).",
                  {"num_segments": len(segments), "num_failures": len(clip_prep_failures), "failures": clip_prep_failures}, t0=t0)

    if not segments:
        yield _event("CLIP_PREP", "blocked", "No clips could be prepared for rendering.", {}, t0=t0)
        raise PipelineBlocked("no clips prepared")

    # --- MEDIAPIPE + RENDER -------------------------------------------------
    yield _event("RENDER", "running", "Extracting body, hand and face landmarks; rendering sign-language avatar...", t0=t0)
    from spike_render_captioned_lesson import render_lesson
    final_out_path = os.path.join(output_dir, "final_episode.mp4")
    motion_json_path = os.path.join(output_dir, "motion", "motion.json")
    segments_dir = os.path.join(output_dir, "segments")
    render_lesson(segments=segments, norm_dir=motion_dir, out_dir=segments_dir,
                  motion_json_path=motion_json_path, final_out_path=final_out_path)
    actual_duration_s = probe_duration_s(final_out_path)
    validation["duration_plan"]["actual_duration_s"] = actual_duration_s
    with open(os.path.join(output_dir, "validation.json"), "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, ensure_ascii=False)
    timed("RENDER")
    yield _event("RENDER", "done", "Sign-language avatar video rendered.", {
        "final_video": "final_episode.mp4",
        "requested_duration_s": duration_plan["requested_duration_s"],
        "estimated_duration_s": duration_plan["estimated_duration_s"],
        "actual_duration_s": actual_duration_s,
    }, t0=t0)

    # --- TRACEABILITY -----------------------------------------------------
    yield _event("TRACEABILITY", "running", "Building segment-level traceability...", t0=t0)
    trace = build_traceability(manifest, included_units, seg_trace)
    write_traceability_json(trace, os.path.join(output_dir, "traceability.json"))
    write_traceability_markdown(trace, os.path.join(output_dir, "traceability.md"))
    timed("TRACEABILITY")
    yield _event("TRACEABILITY", "done", f"{len(trace['segments'])} rendered segments traced to source spans.",
                  {"num_segments_traced": len(trace["segments"])}, t0=t0)

    stage_timings["TOTAL"] = round(time.time() - t0, 2)
    with open(os.path.join(output_dir, "stage_timings.json"), "w", encoding="utf-8") as f:
        json.dump(stage_timings, f, indent=2)

    yield _event("DONE", "done", "Pipeline complete.", {"stage_timings": stage_timings}, t0=t0)
