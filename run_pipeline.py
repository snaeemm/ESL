#!/usr/bin/env python3
"""
One-command orchestrator (build order Step 17):

  SOURCE -> UNDERSTAND -> STRUCTURE -> SIGN PLAN -> TERMINOLOGY
  -> SIGN RESOLUTION -> DURATION PLANNING -> VALIDATE -> CLIP PREP
  -> MEDIAPIPE -> RENDER -> TRACEABILITY

This is a thin CLI wrapper — all actual stage logic lives in
lib/pipeline_runner.py's run() generator, which is the SAME code path
the web application's backend job worker calls (webapp/backend). Neither
duplicates the other's business logic.

Run with (see README.md for full environment setup):

  uv run --python 3.11 \
    --with requests --with opencv-python --with "mediapipe==0.10.14" --with numpy \
    --with arabic-reshaper --with python-bidi --with Pillow \
    python3 run_pipeline.py --source content/grade6_science_ch3_cells.md --output outputs/run_001

Fails fast and clearly (not with a buried stack trace) if Ollama isn't
reachable, the Falcon model isn't pulled, ffmpeg is missing, or
validation blocks rendering.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from lib.pipeline_runner import run, PipelineBlocked
from lib.understand import DEFAULT_MODEL


def main():
    ap = argparse.ArgumentParser(description="SOURCE -> UNDERSTAND -> STRUCTURE -> ... -> SIGN VIDEO")
    ap.add_argument("--source", required=True, help="Path to a .md/.txt academic source file")
    ap.add_argument("--output", required=True, help="Output directory for this run (must not already exist)")
    ap.add_argument("--source-language", default="auto", choices=["auto", "en", "ar"])
    ap.add_argument("--target-duration", type=int, default=45, help="Target episode length in seconds (approx)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Local Ollama model (default: the benchmark-winning Falcon-H1)")
    ap.add_argument("--allow-review-render", action="store_true",
                     help="Permit rendering a clearly-marked prototype video when validation is REVIEW_REQUIRED (never on BLOCKED)")
    ap.add_argument("--skip-clip-prep", action="store_true",
                     help="Stop after VALIDATE (useful for testing UNDERSTAND/STRUCTURE/SIGN RESOLUTION without network/MediaPipe cost)")
    args = ap.parse_args()

    if os.path.exists(args.output):
        print(f"ERROR: output directory already exists: {args.output} (each run gets its own dir)", file=sys.stderr)
        sys.exit(1)

    try:
        for event in run(
            source_path=args.source, output_dir=args.output, source_language=args.source_language,
            target_duration=args.target_duration, model=args.model,
            allow_review_render=args.allow_review_render, skip_clip_prep=args.skip_clip_prep,
        ):
            if event["status"] == "running":
                print(f"\n{'='*70}\n=== STAGE: {event['stage']}\n{'='*70}", file=sys.stderr)
                print(f"  {event['message']}", file=sys.stderr)
            elif event["status"] == "done":
                print(f"  DONE: {event['message']}", file=sys.stderr)
                if event["data"]:
                    for k, v in event["data"].items():
                        print(f"    {k}: {v}", file=sys.stderr)
            elif event["status"] == "blocked":
                print(f"  BLOCKED: {event['message']}", file=sys.stderr)
    except PipelineBlocked as e:
        print(f"\nPipeline stopped: {e}", file=sys.stderr)
        print(f"See {args.output}/review_required.md and validation.json for detail.", file=sys.stderr)
        sys.exit(2)

    print(f"\nRun directory: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
