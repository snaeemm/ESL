# Checkpoint — known-working baseline

Recorded: 2026-08-22, before pipeline-integration work (SOURCE → UNDERSTAND → STRUCTURE → GENERATE → VALIDATE → SIGN VIDEO) begins.

## Known-working renderer

- `scripts/spike_cartoon_avatar.py` — MediaPipe Holistic extraction, EMA smoothing, hand-gap holding, expression-driven face, procedural 2D avatar renderer. Confirmed working, unmodified in this checkpoint.
- `scripts/spike_render_captioned_lesson.py` — multi-segment lesson assembly: per-segment detection, global scale/anchor normalization, captioned rendering, ffmpeg crossfade concatenation. Confirmed working, unmodified in this checkpoint.

## Known-working output

- `data/zho/spike_mediapipe/lesson/lesson_captioned_xfade.mp4`
  - 640×360, 25fps, duration 73.28s (ffprobe-measured)
  - Produced by the 29-segment hardcoded `SEGMENTS` list in `spike_render_captioned_lesson.py`
  - Confirmed identical (MD5 match) to `~/Desktop/sign_language_lesson.mp4`

## Benchmark evidence (preserved as-is, not modified by pipeline work)

- `benchmarks/llm_grounding/` — grounding-faithfulness benchmark, 4 models, Falcon-H1-7B-Instruct winner (cosine 0.908, ROUGE-1 0.755, ROUGE-L 0.734, Jaccard 0.664, BLEU 0.597, source-span 85.7%).
- `benchmarks/alyah/` — supplementary Emirati-dialect benchmark, 1,173 MCQs, Falcon-H1-7B 64.88% accuracy (secondary/supporting evidence, not the primary model-selection benchmark).

## Current limitations at checkpoint time (see REPO_TECHNICAL_AUDIT.md for full detail)

- No STRUCTURE/GENERATE/VALIDATE pipeline stages exist yet — only SOURCE (ZHO indexing) and SIGN VIDEO (avatar rendering) are implemented, plus a standalone UNDERSTAND benchmark script not yet wired into anything.
- No requirements/pyproject.toml exists (being added as part of this work — see `pyproject.toml`).
- Not under version control at checkpoint time — `git init` performed immediately after writing this file, before further code changes.
- `.env` (Hugging Face token) exists in the working tree; excluded via `.gitignore` before the first commit, never committed.

## Environment confirmed available at checkpoint time

- `ollama` (`/opt/homebrew/bin/ollama`), models pulled: `qwen3.5-9b:q4`, `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, `jais-adaptive-q4:7b`, `qwen3:latest`.
- `ffmpeg` (`/opt/homebrew/bin/ffmpeg`).

## Rule going forward

Nothing under "Known-working renderer" or "Known-working output" above is to be deleted or rewritten by the pipeline-integration work that follows this checkpoint. `spike_render_captioned_lesson.py` may receive a minimal, additive change (accepting a generated segment list as a parameter) — see `README.md` for what changed and why.
