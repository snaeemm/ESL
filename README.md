# AI-Powered Sign Language Academic Video Generator - Prototype

UAE MoE AI Center of Excellence case study prototype. Converts a verified academic source document into a short, source-traceable educational video in Arabic Sign Language, using UAE/ZHO-sourced sign assets and local-only AI inference.

## Demo videos

**Website walkthrough demo:**

https://github.com/user-attachments/assets/857207ca-34fc-43f4-8394-87e9d4131683

Narrated click-through of the `/demo` presentation view against the hero run (job `013fbd2aa3f0`, "My Family and My Day at School") - 100% verified institutional (ZHO) sign coverage, zero fingerspelling, zero review-required items. Covers source verification, the real AI-vs-deterministic pipeline stages with measured timings, the generated episode, sign plan, review policy, traceability, the local-model selection benchmark, and architecture. Rendered with a fix (see `scripts/spike_render_captioned_lesson.py`) that damps hand jitter introduced by an earlier avatar-scale correction, measured and verified against the pipeline's own exported motion data.

**Prototype lesson demo:**

https://github.com/user-attachments/assets/2ffcfe8c-1900-492c-964d-21675ad28ed6

The generated lesson episode itself (job `013fbd2aa3f0`, "My Family and My Day at School"), ~51s, 22 semantic units: **86.4% ZHO institutional coverage / 13.6% ESL Zayed supplementary, 0% fingerspelling fallback, 0 unsupported items** - `overall_status: PASS`. Rendered with the hand-jitter fix described in `scripts/spike_render_captioned_lesson.py`.

## 1. Challenge

Turn approved academic source material into a short sign-language video for students, while keeping every taught fact traceable back to the source, flagging (never guessing) uncertain vocabulary/sign coverage, running all core AI inference locally, and leaving a clear checkpoint for human review before anything ships.

## 2. Architecture

```
SOURCE (hashed .md/.txt, EN or AR)
  -> UNDERSTAND (local Falcon-H1-7B via Ollama: grounded concept extraction,
                 deterministic source-span verification)
  -> STRUCTURE (Episode Builder: verified concepts -> short educational sentences)
  -> SIGN PLAN (semantic decomposition: meaning, not just key_terms)
  -> TERMINOLOGY (contextual EN->AR term translation for unresolved items,
                   only when the source is English)
  -> SIGN RESOLUTION (deterministic match against the 1,143-entry ZHO catalog,
                       or Arabic-fingerspelling fallback - NO model involved)
  -> VALIDATE (deterministic provenance/coverage checks; can BLOCK rendering)
  -> CLIP PREP (download + auto-trim ZHO clips, cached)
  -> MEDIAPIPE + RENDER (reuses the existing procedural avatar renderer)
  -> TRACEABILITY (every rendered segment traced back to its source span)
```

Every stage writes a JSON artifact to `outputs/<run>/` (see §17 below). Nothing generated downstream is ever treated as a new fact - the original source file is the sole authority throughout.

Language independence: SOURCE, UNDERSTAND, and STRUCTURE work on either English or Arabic/MSA source text without code changes (`--source-language auto|en|ar`). TERMINOLOGY only runs when the source is English and an item needs an Arabic term for fingerspelling; if the source is already Arabic, its own terminology is preserved rather than translated.

## 3. Local model selection (why Falcon)

`benchmarks/llm_grounding/` - a grounding-faithfulness benchmark (cosine similarity, ROUGE-1/L, Jaccard, BLEU, and a source-span verbatim-match rate) on the real Cells source text, across 4 local Ollama models:

| Model | Cosine | ROUGE-1 | ROUGE-L | Jaccard | BLEU | Source-span match | Valid JSON? |
|---|---|---|---|---|---|---|---|
| **Falcon-H1-7B-Instruct** | **0.908** | **0.755** | **0.734** | **0.664** | **0.597** | 85.7% | ✅ |
| Qwen3.5-9B | 0.808 | 0.574 | 0.522 | 0.484 | 0.310 | 88.9% | ✅ |
| Qwen3-8B | 0.793 | 0.576 | 0.503 | 0.470 | 0.315 | 60.0% | ✅ |
| jais-adaptive-7B | 0.510 | 0.120 | 0.094 | 0.116 | 0.000 | 0% | ❌ |

**Falcon-H1-7B-Instruct wins every metric the brief names** and was selected as the prototype model on that basis, not preference. `benchmarks/alyah/` is a **secondary, supporting** benchmark (1,173-question Emirati-dialect MCQ eval) - informative regional-language context, not the primary selection criterion, and not conflated with source-grounding accuracy anywhere in this codebase:

| Model | Alyah accuracy |
|---|---|
| **Falcon-H1-7B-Instruct (Q4_K_M)** | **64.88%** (761/1,173) |
| Qwen3:latest | 64.11% |
| jais-adaptive-q4:7b | 51.41% |
| Qwen3.5-9b:q4 | 26.00% |

(source: `benchmarks/alyah/results/alyah_eval_FINAL.log`)

**Prototype vs. production model:** the prototype uses one quantized 7B model chosen from this specific benchmark, on available local hardware. Production model selection would repeat the same evaluation framework across stronger, still-locally-deployable candidates as infrastructure allows (larger Falcon variants, GPU inference, vLLM/llama.cpp serving, possible domain fine-tuning with before/after evaluation - never assumed to help without measuring). **A developer-reported ~83% figure for a larger/different Falcon configuration on a related vocabulary/language evaluation was checked against this repository and is not backed by any script or result file here** - it is DEVELOPER-REPORTED / NOT YET VERIFIED IN THIS REPOSITORY, and is not presented as measured prototype evidence anywhere in this codebase.

## 4. Why MediaPipe

`scripts/spike_cartoon_avatar.py` uses MediaPipe Holistic (pose + both hands + 468-point face, one pipeline). Engineering rationale (not all independently re-measured in this repo):

- Dedicated 21-point-per-hand landmarks are critical for sign language specifically - finger articulation carries meaning.
- One model gives body + both hands + face together, rather than stitching separate systems.
- Runs locally, CPU-only, ~30fps on an M1 Pro (**MEASURED**, stated in the script's own docstring).
- No training required - usable immediately within a two-week prototype window.
- Already integrates directly with the deterministic renderer this prototype reuses.

Alternatives considered: YOLO-pose was directly tested on this machine - body-only (17 COCO keypoints, no hands/face) and slower (5.2fps CPU-default vs MediaPipe's 30fps) on the same clip (**MEASURED**, per `data/zho/spike_mediapipe/AVATAR_HANDOFF.md`). OpenPose was assessed via external published comparisons, not locally benchmarked in this repo (**ENGINEERING ASSESSMENT / NOT MEASURED HERE**) - reported as generally weaker on dedicated hand tracking than MediaPipe's hand model. No benchmark numbers are invented beyond what these two sources actually state.

## 5. Sign vocabulary source

`data/zho/catalog.json` - 1,143 entries from the UAE ZHO (Zayed Higher Organization) government sign-language dictionary, indexed via `scripts/zho_index.py`. This is a **UAE/ZHO verified lexical sign asset** set, not a claim of complete Arabic Sign Language grammar coverage. `data/zho/coverage_report.md` documents the dictionary is signed by 3 distinct people; Episode 1's science vocabulary has only 1/24 direct term matches (ZHO is general-vocabulary, not science-domain - expected and documented).

## 6. Semantic sign planning (not word-for-word)

Per the explicit MoE requirement to preserve **educational meaning** over literal word-for-word translation, `lib/sign_plan.py` asks Falcon to break each educational sentence into a small ordered list of semantic items (entities/actions/relationships - e.g. `["MEMBRANE", "CONTROL/REGULATE", "ENTER", "LEAVE", "CELL"]`), not just the sentence's key_terms. This is explicitly a **semantic sign plan**, not a claim of validated Arabic Sign Language grammar or word order. Where the model can't produce a faithful breakdown, it returns nothing and the unit is marked `REVIEW_REQUIRED` rather than a guessed decomposition.

## 7. Fingerspelling fallback

Every semantic-plan item is resolved deterministically (`lib/sign_resolver.py`) against `catalog.json` (exact case-insensitive match, no fuzzy matching that could change meaning - per `coverage_report.md`'s own documented rejection of substring matching). If no verified lexical sign exists and the source is English, `lib/terminology.py` asks Falcon for **one contextual** Modern Standard Arabic term (using the item's own sentence/span as context, not an isolated word lookup) - sanity-checked deterministically (single clean Arabic-script term, no commentary/alternatives) before use. `lib/fingerspell.py` then deterministically decomposes that Arabic word into letters and looks each one up in `data/zho/arabic_alphabet_map.json` (a static, manually-built, documented mapping - see that file's own `_notes` for how the two ZHO catalog ambiguities were resolved) against the 35-entry verified ZHO Alphabets set.

Every result is labeled `VERIFIED_SIGN` or `FINGERSPELL_CANDIDATE`/`UNSUPPORTED`/`REVIEW_REQUIRED` - **fingerspelling is never presented as equivalent to a verified lexical sign.** Two separate coverage numbers are always reported and never conflated:

- `verified_lexical_sign_coverage_pct` - real ZHO dictionary signs only.
- `renderable_coverage_with_fallback_pct` - includes fingerspelling. **This is a renderability number, not a sign-language-accuracy number.**

## 8. Human review

`lib/validator.py` produces `validation.json` (machine-readable, `PASS`/`PASS_WITH_FALLBACK`/`REVIEW_REQUIRED`/`BLOCKED`) and `review_required.md` (human-readable), split into two distinct questions per the brief:

- **ACADEMIC REVIEW** - does the episode preserve curriculum meaning? (subject-matter teacher)
- **SIGN-LANGUAGE REVIEW** - is the signed representation linguistically appropriate? (qualified UAE/Arabic Sign Language expert)

**This prototype's developer is not a qualified Arabic Sign Language linguist.** No part of this system - LLM output, dictionary matching, MediaPipe tracking, or successful rendering - is treated as proof of linguistic correctness anywhere in the code or this document. A `BLOCKED` status (broken provenance) always stops rendering. A `REVIEW_REQUIRED` status only renders if `--allow-review-render` is explicitly passed, and the artifact remains marked pending review - its status is never silently upgraded.

## 9. Avatar / motion pipeline (reused, not rebuilt)

`scripts/spike_cartoon_avatar.py` and `scripts/spike_render_captioned_lesson.py` are unchanged except one additive refactor: `render_lesson()` now accepts a generated segment list, defaulting to the exact original hardcoded `SEGMENTS` list when called with no arguments - so the original `lesson_captioned_xfade.mp4` remains byte-for-byte reproducible via `python scripts/spike_render_captioned_lesson.py`. Real MediaPipe Holistic tracking, EMA smoothing, hand-gap holding, per-clip/per-lesson global scale+anchor normalization, and ffmpeg crossfade assembly are all reused unmodified. See `CHECKPOINT.md` for the frozen baseline record.

**Why a deterministic real-motion avatar over a generative/deepfake approach:** the developer has prior published sign-language deepfake-generation research (different objective, different sign-language context, and infrastructure/training requirements inappropriate for a two-week prototype). A more generative neural sign-video approach could achieve higher visual realism under the right conditions, but for this case study it would require substantial domain-specific training data, expensive training/inference resources, harder controllability, harder source-to-motion traceability, and worse behavior on unsupported vocabulary. This prototype deliberately favors verified real sign motion → extracted landmarks → deterministic avatar rendering, as a prototype/production engineering trade-off based on available resources, explainability, local deployment, and MoE's traceability requirements - not a claim that the deterministic approach is universally superior. Production may reassess learned/generative motion once sufficient expert-validated data and infrastructure exist.

## 10. How to install

```bash
# Python deps (see pyproject.toml for the full list/rationale)
uv venv --python 3.11
uv pip install -e .

# External requirements (not pip-installable):
brew install ffmpeg
brew install ollama
ollama serve &
ollama pull hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M
```

## 11. How to run

```bash
uv run --python 3.11 \
  --with requests --with opencv-python --with "mediapipe==0.10.14" --with numpy \
  --with arabic-reshaper --with python-bidi --with Pillow \
  python3 run_pipeline.py --source content/grade6_science_ch3_cells.md --output outputs/run_001
```

Useful flags: `--source-language auto|en|ar`, `--target-duration 45`, `--allow-review-render`, `--skip-clip-prep` (stop after VALIDATE - useful for testing UNDERSTAND/STRUCTURE/SIGN RESOLUTION without network/MediaPipe cost), `--model <ollama-model>`.

The command fails fast with a specific message (not a buried stack trace) if Ollama isn't reachable, the model isn't pulled, ffmpeg/uv are missing, or validation blocks rendering.

## 12. Outputs

```
outputs/<run>/
  source_manifest.json    # hash, path, language, timestamp
  understanding.json      # extracted concepts + source_span_verified flags
  episode.json            # structured units: sentence, semantic_sign_plan, sign_resolution
  validation.json         # PASS | PASS_WITH_FALLBACK | REVIEW_REQUIRED | BLOCKED + coverage
  review_required.md      # human-readable academic + sign-language review artifact
  motion/norm/*.mp4        # prepared (downloaded+trimmed) sign clips for this run
  motion/motion.json       # per-segment MediaPipe motion export
  segments/*.mp4            # individually rendered captioned segments
  final_episode.mp4          # the final crossfade-assembled video
  traceability.json / .md    # every rendered segment traced to its source span
```

## 13. Evaluation

See §3 above. `benchmarks/llm_grounding/` is the primary content-understanding benchmark; `benchmarks/alyah/` is secondary/supporting. Both are preserved unmodified as evidence, separate from any application code.

## 14. Prototype limitations (stated precisely, not glossed over)

- **Not linguistically validated Arabic Sign Language.** No qualified sign-language expert has reviewed any output. See §8.
- **ZHO alone does not define a complete natural sign language**; it is a general-vocabulary government dictionary with near-zero direct science-domain coverage (1/24 terms for the development episode) - fingerspelling is the primary path for this specific episode, not an edge case.
- **No cross-signer motion standardization.** Mitigated only by fingerspelling everything with a single consistent signer (Signer A), never mixing presenters mid-episode.
- **Educational-sentence grounding check is a crude vocabulary-overlap heuristic**, not a factuality prover - it catches "the sentence shares no words with its own source span," nothing subtler.
- **Semantic sign planning and terminology translation are LLM outputs**, sanity-checked deterministically but not linguistically validated - always reviewable via `review_required.md`, never presented as certain.
- **Sign transitions are ffmpeg crossfade dissolves**, not pose-space motion blending between signs.
- **No unlimited vocabulary claim.** Coverage is exactly what `validation.json`'s coverage numbers say for a given run, nothing more.
- **No production-readiness claim.** This is a two-week case-study prototype.

## 15. Production path

**Phase 1 (prototype -> improved prototype):** wire in real curriculum-approved source text; strengthen the grounding heuristic; add caching/parallelization to clip prep.
**Phase 2 (validated sign-language system):** qualified UAE/Arabic Sign Language expert review of gloss sequences and fingerspelling; licensed/curriculum-specific sign corpus; sentence/phrase-level sign data and non-manual grammar markers; pose-space transition blending; expert terminology governance.
**Phase 3 (production deployment):** GPU-served stronger local models (benchmark-driven, re-evaluated per §3); precomputed/cached motion library; batch lesson generation; model/version registry; audit logging; monitoring; production-quality 2D/3D avatar rig where justified by evidence.

## 16. Security / data handling

No secrets are read by any pipeline code (`run_pipeline.py`/`lib/`). The repo's `.env` (a Hugging Face token) is unrelated to this pipeline and is git-ignored, never committed. All inference is local (Ollama); the only network calls are to the public ZHO government dictionary/Vimeo CDN for clip download (`lib/clip_prep.py`, reusing `scripts/zho_download.py`). No student/user data is collected or stored.

## 17. Scalability

Per-clip MediaPipe extraction and rendering are sequential (no batching implemented in this prototype). Clip download/trim results are cached by catalog ID (`lib/clip_prep.py`) so repeated signs across runs/episodes are never re-processed. Scaling to many lessons would need parallel clip prep and precomputed motion caching at the catalog level - see Production path §15.

## 18. Web Application

A local FastAPI + React web app (`webapp/`) wraps `run_pipeline.py`/`lib/pipeline_runner.py` for demonstration purposes - it contains **no pipeline business logic of its own**; both the CLI and the web backend call the exact same `lib/pipeline_runner.py:run()` generator.

**Architecture:**
```
webapp/backend/   FastAPI - thin job API around lib/pipeline_runner.py, in-memory job manager
                   with a background worker thread per job (no Redis/Celery - unnecessary at
                   this scale), per-job isolated output dir under outputs/webapp_jobs/<job_id>/
webapp/frontend/   React + Vite (TypeScript) - Create Lesson, Progress, Results (5 tabs:
                   Lesson, Sign Plan, Review, Traceability, Technical Details), History
```

**Backend startup:**
```bash
cd webapp/backend
uv run --python 3.11 --with fastapi --with uvicorn --with python-multipart \
  --with requests --with opencv-python --with "mediapipe==0.10.14" --with numpy \
  --with arabic-reshaper --with python-bidi --with Pillow \
  uvicorn app.main:app --reload --port 8000
```

**Frontend startup:**
```bash
cd webapp/frontend
npm install   # first time only
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api/*` to the backend on port 8000 (see `webapp/frontend/vite.config.ts`) - no hardcoded absolute URLs.

**Local dependencies:** same as §10 (Ollama + Falcon-H1 model pulled, ffmpeg, uv), plus `fastapi`/`uvicorn`/`python-multipart` for the backend and Node.js/npm for the frontend.

**Example workflow:** paste or upload a `.txt`/`.md` academic source on the Create Lesson screen → choose source language / duration / review mode → Generate Lesson → the Progress screen polls real pipeline stage events (`lib/pipeline_runner.py`'s own yields - never simulated) → on completion, the Results dashboard shows the video, real coverage/traceability metrics read live from that run's JSON artifacts, and downloadable reports.

**Network disclosure:** core AI inference (Falcon-H1 via Ollama) runs entirely locally. The app is NOT fully offline: `lib/clip_prep.py` may reach the public UAE ZHO government dictionary and its Vimeo CDN to download sign clips not already cached under `data/zho/clips/`. No cloud generative-AI API is called anywhere.

**Security:** uploaded sources are copied into per-job isolated directories under `outputs/webapp_jobs/`, filenames are sanitized (`app/jobs.py:sanitize_filename`), only `.txt`/`.md` uploads up to 2MB are accepted, downloadable artifacts are restricted to an explicit allowlist (`main.py:DOWNLOADABLE_ARTIFACTS` - no arbitrary filesystem access), and no `.env`/secrets/model files are ever served by any endpoint.

**Federal visual identity:** the frontend's colour palette, typography, logo, bilingual/RTL, and branding decisions are documented in detail - including what's an official guideline requirement versus a prototype implementation choice, and one disclosed gap (live re-verification of the guideline page was attempted but blocked by the site) - in `docs/FEDERAL_VISUAL_IDENTITY.md`.

**Prototype limitations (web app specifically):** no database (job history is read from `outputs/webapp_jobs/` on disk, capped at 50 most recent); single-worker-thread job execution (no queueing/concurrency limits); no authentication (local-only, single-user prototype); not load-tested; no automated accessibility audit performed (see `docs/FEDERAL_VISUAL_IDENTITY.md` §11).

## 19. Embedding-based candidate retrieval (bilingual ZHO resolution)

Deterministic exact-match resolution (§7) is the primary path. `lib/vocab_embedding_st.py` adds an **optional Layer 4b**: local multilingual sentence-embedding retrieval (`sentence-transformers`, CPU-only, no API calls) used only to surface *candidate* catalog ids for Falcon to choose from - embedding similarity itself never authorizes a sign; `lib/sign_resolver.py` still deterministically verifies that whatever id Falcon picks was actually present in the candidate set shown to it (see §H finding in `data/zho/spike_mediapipe/ab_experiment_20260823/FINAL_REPORT.md`: Falcon can attach a garbled label to an otherwise-valid id, which is exactly why this boundary is hard-enforced in code, not just policy).

Two lightweight multilingual candidates were benchmarked against each other and against plain lexical retrieval before either was trusted, per `scripts/vocab_embedding_benchmark.py`:

| Model | Params | Dim | Task | Recall@1 | Recall@5 | Verdict |
|---|---|---|---|---|---|---|
| **MiniLM** (`paraphrase-multilingual-MiniLM-L12-v2`) | ~118M | 384 | 30-pair bilingual EN/AR synonym retrieval | **0.733** | **0.933** | **SELECTED** - beat e5-small, lexical-only, and Ollama `nomic-embed-text` on this task |
| multilingual-e5-small | ~118M | 384 | same 30-pair benchmark | lower | lower | rejected |
| MiniLM (same model) | ~118M | 384 | separate 16-item **sentence/phrase**-retrieval sanity check (15 positive-control cases) | 0.20 | 0.33 | **NOT_USEFUL** - re-tested honestly on a different task rather than assumed to transfer; concrete wrong matches documented (e.g. "greeting someone" → "You are welcome"). Never wired into `lib/sign_resolver.py`. |

Full evidence trail: `data/zho/spike_mediapipe/ab_experiment_20260823/FINAL_REPORT.md` (§C/§D/§AD), `docs/PRESENTATION_EVIDENCE_GAPS.md`.

## 20. Test suite

`tests/` - **77 tests, 9 files, plain `assert`-based** (no pytest dependency required, though `pytest` also runs them directly since they're `test_*` functions). Falcon/Ollama network calls are mocked at the `lib.understand._call_ollama` boundary only; the parse/validation/resolution/rendering logic under test is real, unmocked code.

```bash
source .venv/bin/activate
python -m pytest tests/ -q        # or: python -m tests.test_<name> per-file
```

| File | Tests | Covers |
|---|---|---|
| `test_resolver_regressions.py` | 21 | Sign-resolution hardening: semantic-preservation guard, ambiguous-category disambiguation, ZHO-exact priority over fallbacks |
| `test_esl_zayed_supplementary.py` | 16 | ESL Zayed supplementary-catalog integration guardrails - ZHO always tried first, ESL Zayed candidates rejected if outside the shown candidate set, confidence tiers kept separate in coverage reporting |
| `test_sign_plan_arabic_hints.py` | 8 | Arabic-source vocabulary hints in `lib/sign_plan.py` use the Arabic tokenizer (not the English one, which yields zero tokens on Arabic script); English-source behavior unchanged |
| `test_clip_prep_reconciliation.py` | 7 | ESL Zayed clip materialization - CLIP_PREP no longer silently skips `VERIFIED_SIGN` items resolved via `ESL_ZAYED` (catalog_ref=None, supplementary_ref set) |
| `test_arabic_clitic_normalization.py` | 6 | Arabic clitic/lexical query-side normalization in `lib/vocab_retrieval.py` |
| `test_arabic_caption_field_mapping.py` | 5 | Arabic-caption tofu-box regression: caption text now sourced from the correct verified field per render_source, never a generic `terminology`/`term` fallback |
| `test_catalog_bilingual.py` | 5 | Bilingual ZHO catalog join (word_en/word_ar pairing, integrity flagging of corrupted entries) |
| `test_understand_structured_output.py` | 5 | Bounded structured-output handling: strict parse → lenient field extraction → one bounded repair-retry → deterministic `REVIEW_REQUIRED` if still invalid; no unbounded retries, no content fabrication |
| `test_avatar_scale_resolution_invariance.py` | 4 | Avatar scale/anchor computed per-segment from that segment's own native resolution, not pooled across mixed-resolution segments |

**Benchmarks** (separate from regression tests, preserved as evidence, not re-run automatically): `benchmarks/llm_grounding/` (model selection, §3), `benchmarks/alyah/` (secondary Emirati-dialect eval, §3), `scripts/vocab_embedding_benchmark.py` (embedding retrieval, §19).
