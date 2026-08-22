# Repository Technical Audit

Repo: `/Users/shaz/MOI-Arabic-Sign-Language` — not a git repository (no `.git/`). Audit date 2026-08-21 (updated same day after `benchmarks/` was recovered from a session scratchpad and relocated into the repo — see Update Note). Read-only inspection; nothing in the repo was modified to produce this file except the addition of the `benchmarks/` folder by the user's own action between the initial and updated pass.

**Update note (2026-08-21, later same day):** the initial version of this audit stated no LLM benchmark evidence existed in-repo. That was correct *at the time* — the benchmark scripts and raw results existed only in a session-scoped scratchpad outside this repository. The user has since recovered and relocated them into `benchmarks/`. Sections 3, 5, 6, 19, 24, 26, 27, and 29–31 below have been revised accordingly; all other sections are unchanged from the original pass.

---

# 1. Executive Summary

This repo is a **partially-built prototype for a UAE MoE case study**: turning an academic science lesson into an Arabic Sign Language video. Per the project's own brief (`Brief/AI-Powered Sign Language Academic Video Generator.md`) the intended pipeline is SOURCE → UNDERSTAND → STRUCTURE → GENERATE → VALIDATE → SIGN VIDEO, built in 6 steps.

**What is fully working (VERIFIED FROM CODE / OUTPUT):**
- Step 1: a full crawl/index of the ZHO (UAE government) Sign Language Dictionary — `data/zho/catalog.json` (1,143 entries), download of the 36 clips needed for Episode 1's fingerspelling fallback, and a detailed coverage report (`data/zho/coverage_report.md`).
- A MediaPipe Holistic keypoint-extraction pipeline that reliably tracks pose+hands+face from ZHO video clips (`scripts/spike_cartoon_avatar.py` and siblings).
- A procedural 2D cartoon-avatar renderer driven directly by those keypoints, including temporal smoothing, fixed per-clip scale, and a 29-segment captioned lesson video assembled from real tracked motion (`data/zho/spike_mediapipe/lesson/`).

**What is partially working:**
- A "rigged" (styled Emirati-art) avatar exists in a second, more advanced but unfinished form (`scripts/spike_rigged_render_v2.py`, `data/zho/spike_mediapipe/rigged/`) with a documented unfixed hand-orientation bug.
- The LLM/UNDERSTAND stage: **now confirmed real and in-repo as of this update** (`benchmarks/llm_grounding/`) — a working, reproducible benchmark script that prompts 4 local Ollama models to extract grounded `{concept, key_terms, source_span}` JSON from the real Episode 1 source text, scored on cosine/ROUGE/Jaccard/BLEU/source-span-match, with a clear winner (Falcon-H1-7B). This is genuinely the case study's core "Understand" pipeline stage proven end-to-end on real content — but it is a standalone, manually-run script, not yet wired into an automated pipeline that would call it as part of a larger run.

**What is experimental / abandoned side-track:**
- The entire avatar-rendering effort (`scripts/spike_*.py`, `data/zho/spike_mediapipe/`) is explicitly labeled a side-experiment in its own handoff doc and in the brief itself — not a required deliverable.
- A `yolo11n-pose.pt` model file and a `.venv_live2d` environment and `scripts/test/vrm-poc/` (Node/VRM proof of concept) sit in the repo with no wiring to anything — dead-end explorations.

**What is missing entirely (VERIFIED FROM CODE — absence confirmed by search):**
- No FastAPI backend (`grep -rl "fastapi"` across all `.py` files returns nothing).
- No frontend of any kind (only unrelated `package.json` under `scripts/test/vrm-poc/`).
- No `structure` / `generate` / `validate` / `assemble` pipeline stages as code — these exist only as headers in the brief document. (`understand` now DOES exist, see above — the LLM grounding-extraction benchmark script is a real, working instance of this stage, run standalone rather than wired into a pipeline.)
- No `requirements.txt`, `pyproject.toml`, or environment spec file anywhere — only ad hoc `.venv`/`.venv_live2d` directories.
- No complete Episode 1 output (a full "Cells" lesson turned into a validated ArSL video) — the closest artifact is the captioned lesson video pipeline, which stitches together **English-word test signs** (e.g. "circle," "center," "examine"), not the actual Grade-6-Science-Ch.3 episode content.

**Strongest parts of the project:** the ZHO indexing/coverage work (Step 1) is genuinely thorough, reproducible, and honestly documents real findings (multi-signer discovery, API reverse-engineering, coverage gaps). The MediaPipe keypoint pipeline and procedural avatar renderer are real, working, and non-trivial engineering (temporal smoothing, gap-holding, per-clip scale stabilization). Both are honestly self-documented with known limitations rather than oversold.

---

# 2. Repository Map

```
/Users/shaz/MOI-Arabic-Sign-Language/
├── Brief/AI-Powered Sign Language Academic Video Generator.md   # the design brief (source of truth for intended architecture). Used as spec, not code.
├── MOI-Task/Case Study 3 - AI-Powered Sign Language Academic Video Generator.pdf  # official MoE prompt (binary PDF, not parsed here)
├── NEXT_SESSION_PROMPT.md        # status/handoff note as of 2026-08-18. Documentation only.
├── content/
│   └── grade6_science_ch3_cells.md   # the ONLY academic source text present in-repo (received 2026-08-18, explicitly labeled a stand-in, not the real approved MoE textbook). STAGE: source input, not yet consumed by any code in this repo.
├── data/zho/
│   ├── catalog.json               # 1,143-entry ZHO dictionary index (word_en, category, video_url, vimeo_id, thumb_path…). STAGE: source vocabulary. Used by download_manifest/scripts.
│   ├── download_manifest.json     # subset of catalog selected for download
│   ├── coverage_report.md         # narrative report: indexing method, signer identity findings, Episode-1 term coverage (1/24 direct match). STAGE: source/vocabulary analysis, used (as a report, not executable).
│   ├── clips/                     # downloaded ZHO clips, 36 files total, under "Alphabets" and "Directions and Locations" categories only
│   ├── thumbs/                    # thumbnail images for indexed entries
│   ├── signer_survey/             # contact_sheet.jpg + legend.txt documenting the 3-signer finding from coverage_report.md
│   └── spike_mediapipe/           # ALL avatar-experiment artifacts (see below) — side-experiment, not required deliverable
├── scripts/
│   ├── zho_index.py                # crawls ZHO's JSON API, builds catalog.json. STAGE: source ingestion (vocabulary). USED (produced catalog.json).
│   ├── zho_download.py             # downloads selected clips per download_manifest.json. STAGE: source ingestion. USED.
│   ├── spike_find_active_window.py # trims a ZHO clip to its active-sign window via first/last hand-detected frame. USED by lesson-render pipeline.
│   ├── spike_cartoon_avatar.py     # MAIN procedural avatar renderer: MediaPipe Holistic extraction, EMA smoothing, hand-gap holding, face-expression mapping, motion JSON export. USED, current working renderer.
│   ├── spike_render_captioned_lesson.py  # assembles 29 rendered ZHO word segments into one captioned video with Arabic+English captions, ffmpeg crossfades, global scale/position normalization across segments. USED, produces `lesson/` output.
│   ├── spike_rigged_render_v2.py   # alternate renderer driving styled Emirati art assets via affine transforms per limb. PARTIALLY working — documented unfixed hand-orientation bug.
│   ├── spike_rigged_render.py      # earlier version of the above (trig-based, superseded by v2 per handoff doc)
│   ├── spike_mediapipe_avatar.py, spike_normalize_and_detect.py, spike_composite_test.py, spike_composite_v2.py  # earlier/exploratory versions, superseded by spike_cartoon_avatar.py — not the current path
│   ├── spike_extract_avatar_parts.py, spike_extract_gemini_sheet.py  # tooling to cut character-art sheets (ChatGPT/Gemini generated) into individual limb PNGs for the rigged renderer
│   ├── test.py, test/, test/trying-avatarIwant/, test/vrm-poc/   # further experimental/dead-end avatar attempts, including a Node.js/VRM 3D-avatar proof of concept unrelated to the Python pipeline
│   └── __pycache__/                # compiled bytecode, ignore
├── data/zho/spike_mediapipe/
│   ├── AVATAR_HANDOFF.md, AVATAR_ASSET_SPEC.md   # design/status docs for the avatar side-experiment
│   ├── holistic_landmarker.task, hand_landmarker.task   # MediaPipe model files (Tasks API — NOT the API actually used; see §10)
│   ├── trimmed/                    # per-clip trimmed videos + per-clip motion JSON (e.g. `alif_motion.json`)
│   ├── lesson/                     # OUTPUT of spike_render_captioned_lesson.py: 29 word-segment .mp4s (e.g. circle.mp4, center.mp4, examine.mp4…), a captioned/ subfolder, concat lists, and `lesson_motion.json` (the multi-segment motion export)
│   ├── rigged/, avatar_parts/, sentence/, paragraph/, normalized/  # intermediate/exploratory renders and extracted art assets for the rigged-avatar track
│   └── overlay*.mp4, stick_avatar*.mp4   # early-stage keypoint-overlay and stick-figure proof-of-concept videos
├── scratch/                        # standalone HTML viewer pages (avatar_page.html, lesson_page.html, pivot_tool.html, etc.) — throwaway local visualization/debug tools, not part of any pipeline
├── yolo11n-pose.pt                 # a YOLO pose-estimation model weights file — evaluated per AVATAR_HANDOFF.md notes (compared against MediaPipe) but not wired into any current script
├── emirati_garb_illustration.png   # a standalone reference/concept image, not consumed by code
├── .venv/, .venv_live2d/           # two separate Python virtualenvs, no requirements files backing either
├── .env                            # contains one key: `hf_token` (see §20)
└── .claude/                        # Claude Code project settings, not part of the application
```

Ignored: `.DS_Store` files, `__pycache__/`, `.venv*/lib/` contents (standard installed packages).

---

# 3. Actual End-to-End Pipeline

Per the brief, the intended pipeline is SOURCE → UNDERSTAND → STRUCTURE → GENERATE → VALIDATE → SIGN VIDEO. Reconstructed against actual code:

| Stage | Exists? | Input | Processing | Model/Library | Output | Automated/Manual |
|---|---|---|---|---|---|---|
| **SOURCE** | Partially | `content/grade6_science_ch3_cells.md` (academic text); `data/zho/catalog.json` (sign vocabulary) | ZHO site crawled via reverse-engineered JSON API (`scripts/zho_index.py`); clips downloaded (`scripts/zho_download.py`) | `requests`/`curl`-style HTTP calls (VERIFIED FROM CODE, `zho_index.py`) | `catalog.json`, `download_manifest.json`, downloaded clips | Automated (vocabulary ingestion); the academic text itself was manually supplied, not ingested by any parser/loader script — no PDF/text extraction code exists for `content/grade6_science_ch3_cells.md` |
| **UNDERSTAND** | Yes, as a standalone benchmark script (not yet called by any pipeline orchestrator) | `content/grade6_science_ch3_cells.md` (English source text) | Prompts each of 4 local Ollama models for a structured JSON array of `{concept, key_terms, source_span}` grounded in the source; scores cosine/ROUGE/Jaccard/BLEU + source-span verbatim-match | Ollama-served local LLMs (`qwen3:latest`, `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, `jais-adaptive-q4:7b`, `qwen3.5-9b:q4`) via `benchmarks/llm_grounding/run_ch3_benchmark.py` | Per-model JSON extractions (`benchmarks/llm_grounding/results/*.json`) + scored comparison log (`ch3_benchmark_results_v3_FINAL.log`); winner Falcon-H1-7B | Would feed STRUCTURE, but nothing currently calls this script automatically or consumes its output downstream | Automated per-run (a script you execute), not automated end-to-end (no orchestration wiring it to the rest of the pipeline) |
| **STRUCTURE** | Not implemented | — | — | — | — | DOCUMENTED BUT NOT IMPLEMENTED. No lesson-structuring/script-generation code found. |
| **GENERATE** (text→gloss/sign lookup) | Not implemented | — | — | — | — | DOCUMENTED BUT NOT IMPLEMENTED. No vocabulary-matching, fingerspell-fallback, or confidence-flagging code operates on the academic content. The 29-segment lesson video (§16) uses hand-picked **English word labels** (circle, center, examine…), not output of any generate stage. |
| **VALIDATE** | Not implemented | — | — | — | — | DOCUMENTED BUT NOT IMPLEMENTED. No review/approval UI or flagging logic exists in code. |
| **SIGN VIDEO** | Partially | Per-clip MediaPipe motion data | Procedural rendering (`spike_cartoon_avatar.py`) + segment concatenation with ffmpeg crossfades (`spike_render_captioned_lesson.py`) | OpenCV (`cv2`), MediaPipe Holistic, ffmpeg (external binary, invoked via subprocess — not verified further here) | `lesson/*.mp4`, captioned final video | Automated rendering, but the underlying content is not derived from the SOURCE/UNDERSTAND/GENERATE chain — it's a manually curated demo word list, not Episode 1's actual academic content |

**Bottom line (VERIFIED FROM CODE):** SOURCE (vocabulary ingestion), UNDERSTAND (LLM grounding-extraction benchmark), and SIGN VIDEO (avatar rendering) all exist as runnable code. STRUCTURE, GENERATE, and VALIDATE do not exist in this repository. UNDERSTAND is real and proven on the actual Episode 1 source text — a genuine strength — but it currently runs as a standalone benchmark/comparison script, not as a pipeline stage wired to feed STRUCTURE automatically. The avatar-rendering work, while real engineering, is a rendering back-end proven on **generic word demos**, not on Episode 1 content — so UNDERSTAND and SIGN VIDEO are each independently real, but nothing connects UNDERSTAND's output to what SIGN VIDEO actually renders.

---

# 4. Academic Source Grounding

- Source text: `content/grade6_science_ch3_cells.md` — a single Markdown file (VERIFIED FROM CODE, 3,418 bytes). Its own text (as referenced in the memory doc, not re-quoted verbatim here) states it is a prototype stand-in, not the actual MoE-approved textbook.
- **No chunking, source-ID tagging, page-reference, or citation code exists in this repo.** No script reads this file at all — `grep`-level search across `scripts/*.py` for the filename/content path finds no reference (VERIFIED FROM CODE — absence).
- No grounding prompts, hallucination-prevention logic, or traceability code exists in this repository. Whatever grounding-faithfulness work was reportedly done (cosine/ROUGE/BLEU) is not represented by any file here — no scripts, no prompt templates, no result JSON/CSV.
- **Conclusion: this repository cannot currently prove that any generated content is traceable to the approved source**, because no code path connects the source text to any output. The traceability mechanism described in the brief (source_span verbatim matching, etc.) is DOCUMENTED (in the brief and in external memory) but NOT IMPLEMENTED as code or artifacts in this repo.

---

# 5. Local LLM Experiments

**VERIFIED FROM CODE / OUTPUT-ARTIFACT.** Recovered from a session scratchpad into `benchmarks/` on 2026-08-19 (relocated into this repo 2026-08-21, same numbers as project memory). Two evaluations, both run locally via Ollama against the same 4 candidate models.

**5a. Required grounding-faithfulness benchmark** (`benchmarks/llm_grounding/`, brief §4) — tests concept/key-term/source-span extraction from the real Episode 1 source text (`content/grade6_science_ch3_cells.md`):

| Model | Family | Params | Quant | Runtime | Task | Prompting | Hardware | Latency | Accuracy metric | Result | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M` | Falcon-H1 | 7B | Q4_K_M | Ollama | Grounded concept/term/source-span JSON extraction from Ch.3 source text | Single-pass, temp=0, `repeat_penalty=1.3` | Local (M1 Pro per project memory; not restated in benchmark files themselves) | Not recorded in these files | Cosine/ROUGE-1/ROUGE-L/Jaccard/BLEU/source-span-match | **Winner: cosine 0.908, ROUGE-1 0.755, ROUGE-L 0.734, Jaccard 0.664, BLEU 0.597, source-span 85.7%, 7 concepts, valid JSON** | `benchmarks/llm_grounding/results/ch3_benchmark_results_v3_FINAL.log`, `ch3_extraction_hf.co_tiiuae_Falcon-H1-7B-Instruct-GGUF_Q4_K_M.json` |
| `qwen3.5-9b:q4` | Qwen3.5 | 9B | Q4 | Ollama | Same task | Same, `think:false` (reasoning model) | Local | Not recorded | Same metrics | Cosine 0.808, ROUGE-1 0.574, Jaccard 0.484, BLEU 0.310, source-span **88.9% (best of all 4)**, 9 concepts, valid JSON | `ch3_extraction_qwen3.5-9b_q4.json` |
| `qwen3:latest` | Qwen3 | 8B | Not stated in these files | Ollama | Same task | Same | Local | Not recorded | Same metrics | Cosine 0.793, ROUGE-1 0.576, source-span 60.0%, 10 concepts, valid JSON | `ch3_extraction_qwen3_latest.json` |
| `jais-adaptive-q4:7b` | Jais (2023-era adapt) | 7B | Q4 | Ollama | Same task | Same, plus 7 follow-up mitigation attempts (`retry_jais.py`, `retry_jais_chunked.py`) | Local | Not recorded | Same metrics | Cosine 0.510, ROUGE-1 0.120, source-span 0%, 0 concepts, **reliably fails to produce valid JSON** on full-document pass; with per-section chunking, 3/4 sections succeed, 1 (densest, 4 organelles) fails consistently — a real content-complexity ceiling, not a config bug | `ch3_extraction_jais-adaptive-q4_7b.json`, `jais_chunked_results.json` |

**Winner per the brief's own selection rule** ("best grounding-faithfulness score used in the live demo"): **Falcon-H1-7B-Instruct** — wins every metric the brief explicitly names (cosine/ROUGE/Jaccard/BLEU), narrowly loses only the bonus source-span metric to Qwen3.5-9B.

**5b. Supplementary Emirati-dialect benchmark** (`benchmarks/alyah/`, NOT part of the required deliverable) — TII's public "Alyah" benchmark, 1,173 MCQs, `alyah_test.parquet` present in-repo:

| Model | Accuracy | Parse rate | Evidence |
|---|---|---|---|
| Falcon-H1-7B (winner) | **64.88%** | 100% | `benchmarks/alyah/results/alyah_eval_FINAL.log` |
| Qwen3-8B | 64.11% (statistically ~tied with Falcon-H1) | 100% | same |
| jais-adaptive-7B | 51.41% | 99.5% | same |
| Qwen3.5-9B | 26.00% (collapses despite winning 5a) | 100% | same |

Latency/speed figures are not recorded in any of the recovered benchmark log files themselves — only qualitative hardware context (M1 Pro, local) is available, sourced from project memory rather than the benchmark artifacts.

---

# 6. Evaluation & Metrics

**LLM/content metrics (VERIFIED FROM OUTPUT-ARTIFACT, `benchmarks/`):**
- `benchmarks/llm_grounding/run_ch3_benchmark.py` — cosine similarity (TF-IDF), ROUGE-1/L, Jaccard token overlap, BLEU, and a bonus source-span verbatim-match rate, all scored against the real Ch.3 source text. Sample size: 1 document (the actual, if prototype-stand-in, Episode 1 source), 4 models. Metric definitions match standard NLP summarization/extraction eval practice; the bonus source-span metric is the most directly relevant to this case study's traceability requirement, since it checks the model's claimed quote actually appears verbatim in the source. Limitation: n=1 document is not statistically robust, and metrics are English-only (the LLM stage doesn't touch Arabic per the architecture — see `benchmarks/README.md`).
- `benchmarks/alyah/run_alyah_eval.py` — accuracy + parse-rate against TII's Alyah benchmark (1,173 MCQs, real external dataset, not authored in-house). This is a meaningful, large-sample eval, but it measures general Emirati-dialect comprehension, not this project's actual content-extraction task — useful supporting/model-selection narrative, not a substitute for 5a.
- Both evals are real, reproducible (rerun instructions in `benchmarks/README.md`), and their debugging trails (jais-adaptive JSON-formatting bug, qwen3/qwen3.5 `think:false` gotcha) are documented — this is a genuinely strong "we benchmarked, we didn't just assert" story.

**Sign-language/video/keypoint metrics: still none found.** No jerk/jitter measurement code, no ground-truth keypoint comparison, no sign-recognition accuracy eval exists anywhere in the repository — the avatar/rendering pipeline's quality claims (e.g. "4.5x jerk reduction" cited in code comments) are not backed by a runnable measurement script or logged numbers in-repo; they read as a one-off manual observation, not a saved evaluation artifact.

`data/zho/coverage_report.md` additionally reports **vocabulary coverage counts** (1,143 total ZHO entries, 1/24 direct term matches for Episode 1, 36/36 needed clips downloaded, 3-signer breakdown) — real, in-repo, but a coverage/indexing statistic, not a model-quality or sign-language-quality evaluation.

---

# 7. Content Understanding & Episode Generation

**No code exists for this stage.** No summarization, concept-extraction, key-term-extraction, lesson-structuring, script-generation, grade-adaptation, or Arabic-generation logic operates on `content/grade6_science_ch3_cells.md` anywhere in this repository. This entire section of the intended pipeline is DOCUMENTED (in the brief) BUT NOT IMPLEMENTED.

---

# 8. Arabic Sign Language Transformation

No code transforms educational language into a sign gloss sequence. To be precise about what does and doesn't exist, distinguishing the four categories requested:

1. **Arabic language**: present only as static text — Arabic captions burned into the lesson video via `arabic_reshaper`/`python-bidi`/PIL (per `spike_render_captioned_lesson.py`, referenced in the handoff doc) for the demo word list (e.g. "صباح" for "Morning," visible in `lesson_motion.json`'s `arabic` field per segment). This is hand-authored caption text for a demo, not an LLM-generated or pipeline-generated translation.
2. **Arabic Sign Language gloss/representation**: **not present**. There is no gloss dictionary, no phrase-to-gloss mapping, no ordering/grammar logic. The "signs" rendered are whichever ZHO/demo clips were manually chosen for the avatar-motion demo (circle, center, examine, find, grows, etc. — general vocabulary, not glossed sentences).
3. **Emirati sign-language examples/datasets**: the ZHO dictionary (`data/zho/catalog.json`, 1,143 entries) is a real, government-sourced Emirati/UAE sign vocabulary — VERIFIED FROM OUTPUT-ARTIFACT. This is real data, but it is a **word-level dictionary**, not a phrase/sentence corpus, and per `coverage_report.md` covers only 1 of Episode 1's 24 science terms directly.
4. **Avatar animation**: real, working (see §14) — but it animates whatever motion data it's given; it has no role in deciding *what* signs to animate.

**Do not conflate these.** This repository does not implement "Arabic Sign Language transformation" — it implements (a) a real Emirati/UAE sign vocabulary index, and (b) a real avatar renderer that can play back motion captured from that vocabulary's clips. The connective logic (matching lesson concepts to signs, ordering them, flagging gaps, fingerspelling) does not exist as code.

---

# 9. Sign Vocabulary Dataset

- **Source:** `data/zho/catalog.json` — VERIFIED FROM OUTPUT-ARTIFACT, 1,143 entries, JSON list of objects with schema: `id` (UUID), `word_en`, `category`, `item_path`, `item_url`, `video_url` (Vimeo progressive-download MP4), `vimeo_id`, `thumb_path`, `has_video` (bool).
- **Categories:** 21 total per `coverage_report.md`, e.g. Numbers (116), Professions and Jobs (100), Common Verbs (96), Health (96), Clothing and Toiletries (89), Attributes and Situations (78), Environment (68), Animals (64), Education (61), Sports (46), Ministries Departments (42), Household Items (37), Official Documents (36), Alphabets (35), Measurement Units (33), Popular Cuisines (29), (remainder not enumerated in the head of the report but totals to 1,143).
- **Signers:** per `coverage_report.md` and `data/zho/signer_survey/` (contact_sheet.jpg + legend.txt) — **3 distinct people** identified by visual inspection: Signer A (female, Alphabets category only, 35 entries), Signer B (male, 19/21 categories, 1,062/1,143 entries — 92.9% of the dictionary), Signer C (male, Sports category only, 46 entries). This is a real, documented finding (VERIFIED FROM OUTPUT-ARTIFACT), not inferred.
- **Downloaded clips:** only 36 of the 1,143 catalog entries were actually downloaded (`data/zho/clips/`, 2 subfolders: "Alphabets" and "Directions and Locations", 36 files total) — VERIFIED FROM OUTPUT-ARTIFACT via direct file count. This is the subset needed for Episode 1's fingerspelling fallback per `download_manifest.json`, not the whole dictionary.
- **Duplicate labels:** not checked/reported anywhere in-repo; not independently verified in this audit (would require parsing all 1,143 `word_en` values for exact duplicates — out of scope for a static read-through, flagged as unverified).
- **Vocabulary mapping:** entirely automatic for the indexing step (`zho_index.py` crawls the source API), but Episode-1-specific term coverage was determined **manually** by the report's author cross-referencing the science term list against the catalog (per `coverage_report.md` narrative) — no automatic term-matching code exists.

---

# 10. MediaPipe / Landmark Pipeline

VERIFIED FROM CODE, `scripts/spike_cartoon_avatar.py`:

- **Solution used:** `mp.solutions.holistic.Holistic` (the legacy `mp.solutions` API), explicitly *not* the newer MediaPipe Tasks API — the module docstring states `mediapipe==0.10.14` is required because the current pip release (`1.0.1`) crashes natively on the dev machine (Metal/GPU graph-service fault). Note: `.task` model files (`holistic_landmarker.task`, `hand_landmarker.task`) exist in `data/zho/spike_mediapipe/` but are **not used** by the current renderer — they belong to the newer Tasks API this script explicitly avoids; likely leftover from an earlier exploration.
- **Landmarks tracked per frame:**
  - Pose: 8 named points extracted (`extract_pose_px`) — l/r shoulder, elbow, wrist, hip (subset of the full 33-point pose model).
  - Left/right hand: all 21 landmarks each, in pixel coordinates (`(lm.x * w, lm.y * h)`).
  - Face: a curated ~18-point subset of the 468-point FaceMesh (`face_metrics()`), used to derive 6 scalar expression metrics (mouth_open, mouth_width, eye_open, eye_width, brow_raise, smile) rather than rendering raw mesh geometry.
- **Coordinate system:** MediaPipe returns normalized (0–1) coordinates; the code immediately converts to pixel coordinates via `lm.x * w, lm.y * h` — VERIFIED FROM CODE (`extract_pose_px`, hand-point list comprehensions). Z is retained separately (relative depth) for hands, used only for the "halo" rim-light effect and for the motion-JSON export — not used in 2D positioning.
- **Frame rate:** read from source video via `cap.get(cv2.CAP_PROP_FPS)`, defaulting to 25 if unavailable; used directly to drive output video writing (no resampling/retiming observed in this file).
- **Missing-landmark handling:** per-frame `None` when MediaPipe fails to detect (pose/left_hand/right_hand independently can be `None`); handled downstream by `HandTrack` (hold-last-pose-and-fade for hands, up to `MAX_HOLD = 8` frames) and by simply not drawing the body if pose is `None`.
- **Confidence thresholds:** `min_detection_confidence=0.5, min_tracking_confidence=0.5` (VERIFIED FROM CODE, `main()`).
- **Smoothing:** `smooth_series()` — an EMA (exponential moving average) smoother applied per-channel (pose alpha=0.25, hands alpha=0.3, face alpha=0.25), resetting at every detection gap.
- **Interpolation:** wrist position only, linearly interpolated across detection gaps in `HandTrack.get()`; full hand shape is explicitly NOT interpolated (held instead) — a documented, deliberate design choice explained at length in the code's own docstring, based on a measured jerk-reduction result (not just asserted).
- **Normalization/scaling:** a single fixed `scale_w` (median shoulder width across the whole clip) is computed once per clip and used for all body/limb/head sizing, to avoid frame-to-frame "pulsing" from landmark noise (documented rationale in code comments, consistent with a static camera assumption). Hand size is separately normalized per-frame to a fixed target span around each hand's own centroid (`normalize_hand_scale`).
- **Orientation handling:** none beyond MediaPipe's own anatomical left/right labeling; the code notes (per the handoff doc, not this file) that MediaPipe's "left/right" is subject-relative and mirrored versus screen position for a forward-facing camera — handled by consistent key naming (`l_`/`r_` = subject's own left/right) rather than any explicit rotation correction.
- **Per-frame dimensionality:** pose = 8 points × (x,y[,z]); each hand = 21 points × (x,y[,z]) when present; face = 6 derived scalars (not raw landmark coordinates) — this is a reduced/derived representation, not the full 543-point MediaPipe Holistic output.

---

# 11. Multi-Signer Standardization

**Important finding: there is no true multi-signer standardization pipeline in this repository.** The renderer processes **one clip at a time**, computing its own fixed scale/position constants from that single clip's frames. There is no code that takes landmark data from two *different human signers* and maps both onto one common, shared avatar coordinate system with cross-signer calibration.

What does exist and could be mistaken for it (VERIFIED FROM CODE, `scripts/spike_render_captioned_lesson.py` per the handoff doc's Session 2 notes, not independently re-verified line-by-line in this audit pass):
- **Cross-segment (not cross-signer) normalization**: when assembling the 29-segment lesson video, a two-pass "detect all segments first, then render against one pooled global scale/anchor" approach was used, because each segment is a separate short clip of (per the handoff doc) the same rendering pipeline, and independently computed per-segment scale/position caused visible size/position jumps at cuts. This standardizes *segments*, not *signers*.
- Per `data/zho/coverage_report.md`, the ZHO dictionary itself has 3 distinct human signers, but the coverage report explicitly **recommends avoiding mixing them** (use Signer A only for Episode 1, even switching away from a Signer B clip that has a direct word match) specifically *because* there is no cross-signer normalization solution — i.e., the documented mitigation for the multi-signer problem is "don't mix signers," not "normalize across signers."

**Conclusion:** DOCUMENTED AS A KNOWN GAP (via the coverage report's own recommendation), not implemented as a standardization algorithm. No shoulder-width cross-signer scaling formula, no rotation normalization, no signer-specific calibration code exists.

---

# 12. Motion Representation

Two motion JSON files found (VERIFIED FROM OUTPUT-ARTIFACT):
- `data/zho/spike_mediapipe/trimmed/alif_motion.json` — single-clip format (per `export_motion_json()` in `spike_cartoon_avatar.py`): `{fps, width, height, frames: [{frame, pose, left_hand, right_hand, face}, ...]}`.
- `data/zho/spike_mediapipe/lesson/lesson_motion.json` — multi-segment lesson format: top-level key `segments`, a list of 29 objects, each with its own `stem`, `english`, `arabic`, `fps`, `width`, `height`, and its own `frames` array in the same per-frame shape as above.

**Example schema (fake/sample values, matching the real structure):**
```json
{
  "segments": [
    {
      "stem": "00_morning",
      "english": "Morning",
      "arabic": "صباح",
      "fps": 25.0,
      "width": 640,
      "height": 360,
      "frames": [
        {
          "frame": 0,
          "pose": {
            "l_sh": [407.5, 192.8, -0.31],
            "r_sh": [245.7, 194.9, -0.34],
            "l_el": [421.8, 293.6, -0.24],
            "r_el": [222.0, 295.4, -0.25],
            "l_wr": [430.6, 386.7, -0.41],
            "r_wr": [219.1, 386.1, -0.47],
            "l_hip": [378.1, 387.5, -0.03],
            "r_hip": [279.7, 369.9, 0.03]
          },
          "left_hand": null,
          "right_hand": [[412.1, 388.2, -0.02], "... 21 points total ..."],
          "face": {
            "mouth_open": 0.016,
            "mouth_width": 0.341,
            "eye_open": 0.051,
            "eye_width": 0.208,
            "brow_raise": 0.149,
            "smile": -0.003
          }
        }
      ]
    }
  ]
}
```
- Each pose/hand point is `[x_px, y_px, z_or_null]` — pixel coordinates plus MediaPipe's relative-depth z (VERIFIED FROM CODE, `export_motion_json`).
- `left_hand`/`right_hand` are `null` for frames where that hand wasn't detected (no interpolation baked into the export — the export is the *cleaned/smoothed* signal but preserves detection gaps as `null`, per the docstring: "cleaned (smoothed, hand-scale-normalized) motion data").
- **No explicit sign-boundary or transition metadata** beyond the per-segment grouping itself (segment start/end = clip start/end); no separate "hold" vs "transition" frame tagging.
- **No NPY/NPZ/CSV motion files found** in this repository — only JSON.

---

# 13. Sign Sequencing and Transition Generation

VERIFIED FROM CODE / the handoff doc (Session 2 notes):
- Segments are concatenated via **ffmpeg with crossfades** between segments (`spike_render_captioned_lesson.py`, referenced concat lists `concat_list.txt`/`concat_list_v2.txt` present in `data/zho/spike_mediapipe/lesson/`) — this is a **video-level** transition (visual crossfade), not a motion-level blend between end-pose of one sign and start-pose of the next.
- **No pose-space interpolation/blending/easing between distinct signs** was found — each segment renders its own tracked motion independently; the crossfade is purely a compositing effect at the video-frame level.
- Within a single sign's gap-filling (not between signs), there IS real motion interpolation: `HandTrack` linearly interpolates wrist position across short detection gaps (see §10) — but this is intra-sign noise-bridging, not inter-sign sequencing.
- **No neutral/rest-pose insertion, no coarticulation modeling, no temporal normalization of sign duration** (e.g. stretching a short sign to match a target lesson pace) was found.
- **Conclusion on naturalness (per code, not subjective viewing):** transitions between signs are a video crossfade dissolve, not a motion-continuous animation — the character's pose can jump discontinuously at a cut, softened only by a visual fade, not by any pose-aware blending.

---

# 14. Avatar / Rendering Pipeline

Two distinct avatar prototypes exist:

**1. Procedural flat-shape renderer (`scripts/spike_cartoon_avatar.py`) — the working, current one.**
- **Type:** 2D vector-shape renderer using OpenCV primitives (not a rigged mesh, not a skeleton import into a 3D engine) — explicitly stated in the file's own docstring as a real ceiling versus an actual 3D rig.
- **Rendering framework:** OpenCV (`cv2.fillConvexPoly`, `cv2.ellipse`, `cv2.circle`, custom `draw_capsule` for tapered limb segments).
- **Body rig:** capsule-shaped limbs between tracked shoulder/elbow/wrist keypoints; kandura (robe) drawn as a filled polygon between shoulders and a computed hem with a shading fold; head is a plain circle (simplified — headwear/beard/glasses were tried and explicitly dropped per code comments, "not reaching the target style" and costing debugging time).
- **Hands:** real per-finger capsule chains (`FINGER_CHAINS`) driven directly by the 21 MediaPipe hand landmarks, with a filled palm polygon and an outline-then-fill draw order per finger to avoid neighboring fingers blurring together; an optional "halo" rim-light drawn behind the hand when depth (z) indicates it's held forward, as a partial mitigation for hand-over-face visual clutter.
- **Face:** eyebrows, eyes (ellipses sized by tracked openness/width), and a real curved mouth (quadratic Bezier through a smile/frown-derived midpoint) — driven by the 6 derived `face_metrics()` scalars, not raw mesh geometry.
- **Clothing:** flat kandura/robe shape only; ghutra/agal headwear was attempted and removed (per code comments) — not currently rendered.
- **Coordinate mapping / export:** draws directly in the source video's pixel space; exports both a rendered `.mp4` (via `cv2.VideoWriter`, `mp4v` codec) and the motion JSON described in §12.

**2. Rigged art renderer (`scripts/spike_rigged_render_v2.py`) — unfinished second track.**
- **Type:** 2D sprite-based rigging — real character-art image pieces (`data/zho/spike_mediapipe/avatar_parts/`) transformed per-limb via `PIL.Image.transform(AFFINE)`, driven by two local pivot points per piece (rotate+scale+translate), rather than hand-rolled trigonometry.
- **Known unresolved bug (per the handoff doc, and a placeholder value visible in the referenced code path):** hand orientation uses a placeholder offset instead of the real tracked wrist→index-finger-base vector.
- **Known blocker:** source art quality — generated character-art sheets (ChatGPT/Gemini) had baked-in grid/checkerboard artifacts and no clean alpha, requiring manual extraction tooling (`spike_extract_avatar_parts.py`, `spike_extract_gemini_sheet.py`) and never reaching production quality.
- This track is not the one used to produce the lesson video in §16.

---

# 15. Finger and Hand Animation

VERIFIED FROM CODE, `spike_cartoon_avatar.py`:
- **Individually articulated fingers: yes**, for the procedural renderer — all 5 fingers, each driven by its own MediaPipe hand-landmark chain (`FINGER_CHAINS = [(1,2,3,4),(5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)]`), i.e. up to 4 joints per finger as tracked by MediaPipe's 21-point hand model, rendered as tapered capsule segments (thicker at the knuckle, thinner at the tip) rather than uniform stick lines.
- **Driven directly by MediaPipe hand joints:** yes, real per-frame tracked positions, not an approximated/canned hand pose.
- **Sprite-based hands:** exist only in the separate rigged-art track (`avatar_parts/` includes discrete hand sprites like `g_hand_fist.png`, `g_hand_open.png`, `g_hand_point.png`, `g_hand_thumbsup.png`) — these are a small fixed set of discrete hand shapes, not continuously articulated, and belong to the unfinished rigged renderer, not the working procedural one.
- **Mesh-based/deformation rigging:** not found anywhere in this repository.
- **What's currently possible:** real, continuous, per-frame finger articulation in the procedural (flat-shape) renderer only.
- **What's not possible/not present:** mesh-deformed 3D hand geometry; smooth interpolation between discrete rigged-sprite hand poses (the sprite set is fixed shapes, would require either swapping frames or a bug-fixed affine pipeline).

---

# 16. Prototype Video

Videos found in `data/zho/spike_mediapipe/`:

| File | Notes |
|---|---|
| `overlay.mp4`, `overlay_inside.mp4` | Early proof-of-concept: MediaPipe keypoints drawn as an overlay directly on the source video, not a standalone avatar. |
| `stick_avatar.mp4`, `stick_avatar_inside.mp4` | Earlier, simpler skeleton/stick-figure rendering stage (superseded by the flat-shape renderer). |
| `trimmed/alif_cartoon.mp4` (implied by `alif_motion.json`'s naming; not independently opened as video in this audit) | Single-word ("alif") demo render using the current procedural renderer. |
| `lesson/*.mp4` (29 files: `morning`(implied), `answer.mp4`, `center.mp4`, `circle.mp4`, `examine.mp4`, `explain.mp4`, `find.mp4`, `grows.mp4`, …) and `lesson/captioned/` | Per-segment renders plus a final captioned/crossfaded assembly — real tracked motion from real ZHO clips, English+Arabic captions burned in via `arabic_reshaper`/PIL per the handoff doc. **This is a vocabulary/motion demonstration reel of general ZHO dictionary words, not the Episode 1 "Cells" academic lesson content.** |
| `rigged/rigged_test.mp4`, `rigged_test_v2.mp4`, `rigged_test_v3.mp4`, `rigged_v2.mp4`, `rigged_v3.mp4` | Iterative test renders of the unfinished rigged-art avatar. |

Exact resolution/duration/FPS were not independently probed via `ffprobe` in this audit (no execution of external tools was performed per the read-only constraint); `lesson_motion.json` records per-segment `width: 640, height: 360, fps: 25.0` for the underlying motion data, which is a strong proxy for the corresponding rendered video's parameters but was not directly confirmed against the `.mp4` container metadata.

**None of the videos in this repository represent a complete academic episode.** All are either raw-keypoint overlays, stick-figure demos, or a general-vocabulary word-list reel — not Episode 1 ("Cells," Grade 6 Science Ch.3) content.

---

# 17. Validation / Human-in-the-Loop

**No validation/review code exists in this repository.** No approval-gate UI, no confidence-flagging logic operating on generated content, no expert-review workflow. The brief (`Brief/...md` §5) *proposes* a human-in-the-loop validation stage — this is DOCUMENTED BUT NOT IMPLEMENTED. The only "review" artifact in-repo is the coverage report itself, which is a human-authored analysis document, not a code-driven validation gate.

---

# 18. AI vs Deterministic Components

| Component | AI/ML | Deterministic | Human | Reason |
|---|---|---|---|---|
| ZHO catalog indexing (`zho_index.py`) | No | Yes | No | Straightforward API crawl; no ML needed. |
| Signer identification (3-signer finding) | No | No | Yes | Done by visual/manual inspection per `coverage_report.md`, no ML classifier used. |
| Landmark extraction | Yes (MediaPipe pretrained models) | No | No | Off-the-shelf pose/hand/face detection; not custom-trained in this repo. |
| Temporal smoothing, scale normalization, gap-holding | No | Yes | No | Hand-written EMA/heuristic code, not learned. |
| Avatar rendering (procedural + rigged) | No | Yes | No | Pure geometric drawing code (OpenCV/PIL), no generative model involved. |
| Academic content understanding | N/A — not implemented | N/A | N/A | Stage does not exist in this repo. |
| Sign selection/gloss generation | N/A — not implemented | N/A | N/A | Stage does not exist in this repo. |
| Validation | N/A — not implemented | N/A | N/A | Stage does not exist in this repo. |

---

# 19. Local Deployment

- **Model runtimes present in-repo:** MediaPipe (pip package, `mediapipe==0.10.14` pinned in the script's own run-instructions per its docstring), OpenCV, PIL. `yolo11n-pose.pt` is present but not invoked by any script found.
- **Ollama usage confirmed** (`benchmarks/llm_grounding/run_ch3_benchmark.py`, `benchmarks/alyah/run_alyah_eval.py`) — both call a local Ollama server serving 4 pulled models (`qwen3:latest`, `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, `jais-adaptive-q4:7b`, `qwen3.5-9b:q4`). All 4 are free/open-weight models pulled locally — no external generative-AI API is called for inference, satisfying the "core inference must run locally" constraint for this stage. No vLLM/llama.cpp/Transformers usage found in this repo's own scripts (llama.cpp use for a Jais-2 investigation is documented in project memory as happening outside this repo, via Homebrew CLI, not as repo code).
- **GPU/CPU:** the MediaPipe scripts explicitly target CPU-only Holistic processing (per the docstring's stated ~30fps on an M1 Pro); no GPU-dependent code found in-repo (aside from the unrelated, unused `yolo11n-pose.pt`).
- **Python environment:** two virtualenvs (`.venv`, `.venv_live2d`) exist but **no `requirements.txt`, `pyproject.toml`, or `environment.yml` was found anywhere in the repo** — dependencies are only inferable from `import` statements and docstring `uv run --with ...` invocations (e.g. `spike_cartoon_avatar.py`'s header comment specifies `--with "mediapipe==0.10.14" --with opencv-python --with numpy`).
- **Internet dependencies:** `zho_index.py`/`zho_download.py` require live internet access to the ZHO government site and Vimeo CDN. `.env` holds a Hugging Face token (see §20), implying at least occasional internet access for model downloads elsewhere in the broader project (not evidenced by any script inside this repo, however).
- **External APIs:** none found called from application code in this repo (the ZHO site itself is a public UAE government resource, not a paid/generative AI API).
- **Flag:** none — the LLM inference that does exist (the grounding-extraction benchmark) runs fully locally via Ollama against open-weight models, correctly satisfying the local-inference constraint. The remaining gap is that this LLM stage isn't yet called by anything else (no orchestrator invokes it as part of a larger run) — a wiring gap, not a local-vs-cloud violation.

---

# 20. Security and Data Handling

- `.env` contains one entry: `hf_token=<redacted>` — a Hugging Face access token. **Type identified only; value not read/printed in this audit.** No script in this repository was found to actually read this token (`grep` for `hf_token`/`HF_TOKEN`/`os.environ` usage referencing it across `scripts/*.py` found no match) — it appears to be present for use outside this repo's own scripts, or a leftover from work done via shell/CLI rather than these Python files.
- No other API keys, passwords, or secret-shaped strings were found in tracked files during this audit's `.py`/`.md`/`.json` review.
- No external network endpoints beyond the ZHO/Vimeo domains (public government dictionary + its CDN) are called by any script found.
- No student/user personal data ingestion exists — the only "personal" data present is the ZHO dictionary's own signer video content (public government resource) and the developer's own on-camera test clips (not evidenced as containing any additional PII beyond the signer's likeness).
- No logging framework or persistent log files were found (only ad hoc `print(..., file=sys.stderr)` status messages in the scripts, not written to disk).
- `.env` itself is present in the repo working directory; whether it would be excluded from any future version control (`.gitignore`) could not be checked — **this repo has no `.git/` directory at all**, so no commit history exists to audit either way. If/when this repo is initialized under git, `.env` should be added to `.gitignore` before the first commit.

---

# 21. Performance and Scalability

- **Measured (VERIFIED FROM CODE/docs):** MediaPipe Holistic runs at ~30fps CPU-only on an M1 Pro per the script docstring (stated, not independently re-benchmarked in this audit). YOLO-pose was evaluated per the handoff doc at 5.2fps CPU-default on the same machine — that comparison data lives outside this repo's own artifacts (referenced in `AVATAR_HANDOFF.md` narrative only, no raw benchmark file found here).
- **Inferred bottlenecks:** per-clip MediaPipe extraction is inherently sequential per frame (no batching observed in `main()`'s frame loop); rendering is also a per-frame Python/OpenCV loop — for a full multi-lesson production system, this would scale linearly with total video minutes, with no caching/precomputation of repeated signs observed (each clip's landmarks are recomputed from scratch; there's no cache keyed by clip identity).
- **No LLM inference cost is measurable from this repo** since no LLM code exists here.
- **Parallelization/batching:** not implemented in any script found — everything processes one clip/segment at a time in a single process.
- **Scaling from one lesson to many:** would require, at minimum, precomputing and caching ZHO clip motion data once (rather than per-lesson), and some concurrency in the per-clip MediaPipe extraction step — neither exists today.

---

# 22. Dependencies and Environment

- **Python version:** 3.11 (inferred from `.venv/lib/python3.11` and `.venv_live2d/lib/python3.11` directory names; also explicitly requested via `uv run --python 3.11` in `spike_cartoon_avatar.py`'s docstring).
- **No requirements/pyproject/environment file exists anywhere in the repo** — dependency versions are only recoverable from script docstrings and `import` statements, not centrally declared. Per feedback captured in project memory, `uv` is the intended package manager for this project, consistent with the `uv run --with ...` invocation style seen in script docstrings, though no `pyproject.toml`/lockfile was actually found.
- **Key libraries referenced in code:** `mediapipe==0.10.14` (pinned, explicitly due to a crash in the newer `1.0.1` release on this machine), `opencv-python` (`cv2`), `numpy`, `PIL`/Pillow (rigged renderer), `arabic_reshaper` + `python-bidi` (Arabic caption shaping, per handoff doc — not independently re-verified against this specific script's imports in this pass), and external `ffmpeg` binary invoked for video crossfading/concatenation (per handoff doc narrative).
- **No PyTorch/transformers usage found** in any script in this repository, despite `yolo11n-pose.pt` (a PyTorch/Ultralytics model file) being present — it appears unused by any current script.
- **OS assumption:** macOS (Darwin), specifically noted Metal/GPU-service crash workarounds for both MediaPipe's newer release and (per memory, external to this repo) llama.cpp's Metal backend.

---

# 23. How to Run the Current Prototype

Reconstructed strictly from what the scripts document/support — **there is no single end-to-end "run" path**, because the middle pipeline stages don't exist. What can actually be run, in isolation:

1. **Rebuild the ZHO vocabulary index** (optional — `catalog.json` already exists):
   ```
   python3 scripts/zho_index.py
   ```
   (Exact CLI args not independently re-verified in this pass; inferred from the file's role per `coverage_report.md`.)

2. **Download the clip subset**:
   ```
   python3 scripts/zho_download.py
   ```

3. **Render a single clip's avatar + motion JSON**, per the script's own docstring:
   ```
   uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python --with numpy \
     python3 scripts/spike_cartoon_avatar.py
   ```
   Reads `SPIKE_CLIP` env var (defaults to a trimmed ZHO alif clip), writes an output video + `<stem>_motion.json`.

4. **Render the full captioned lesson demo**: `scripts/spike_render_captioned_lesson.py` (exact invocation/env vars not re-verified line-by-line in this audit pass; its outputs already exist in `data/zho/spike_mediapipe/lesson/`).

**What is broken/missing for a true "source text → sign video" run:** there is no script that takes `content/grade6_science_ch3_cells.md` as input and produces anything — no command exists to run because the UNDERSTAND/STRUCTURE/GENERATE/VALIDATE stages are unimplemented. The closest thing to an "output" today is the general-vocabulary lesson demo reel, which does not depend on the science-content file at all.

---

# 24. What I Actually Built

- **AI/model experimentation:** real and now in-repo (`benchmarks/`) — a completed, reproducible local-LLM grounding-faithfulness benchmark across 4 models on the actual Ch.3 source text, with a clear winner (Falcon-H1-7B) and an honestly-documented debugging trail for the model that failed (jais-adaptive), plus a supplementary 1,173-question Emirati-dialect eval.
- **Academic-content pipeline:** one source file collected (`content/grade6_science_ch3_cells.md`); no processing pipeline built around it in this repo.
- **Sign-language data engineering:** real — a full ZHO dictionary crawl/index (1,143 entries), a documented multi-signer finding, a targeted coverage analysis against Episode 1's term list, and a working clip-download pipeline for the needed subset.
- **MediaPipe/keypoint work:** real and substantial — Holistic pose+hand+face extraction, active-window auto-trimming, EMA temporal smoothing, gap-bridging logic for hands with a measured jerk-reduction result, expression-metric derivation from the face mesh.
- **Standardization:** real but scoped narrowly — fixed per-clip and per-lesson-segment scale/position normalization exists; true cross-signer standardization does not (see §11).
- **Avatar/rendering:** two real prototypes — a working procedural flat-shape renderer (current, in active use) and a partially-working rigged-art renderer (known unfixed hand-orientation bug, art-quality blockers).
- **Evaluation:** limited to the ZHO coverage report (real, quantitative, in-repo); no LLM or sign-language-quality evaluation artifacts exist in this repository.
- **Integration:** the strongest gap — none of the above pieces are wired together into a single pipeline that goes from the academic source text to a validated sign video. Each subsystem exists in isolation.

---

# 25. Strongest Technical Decisions

1. **Reverse-engineering the ZHO site's JSON API instead of browser automation** (`zho_index.py`) — faster, more reliable, and documented with the actual discovered bugs (silent `page` param, locale count mismatch) rather than hand-waved.
2. **Choosing deterministic clip-assembly/avatar-rendering over generative video** — matches the brief's non-negotiable local-inference and traceability constraints, and is independently reinforced by an MoE HR clarification favoring the "financially better" option (per project memory, not this repo's files).
3. **Fixed per-clip scale instead of per-frame** — a specific, correctly-diagnosed fix for a real visible artifact (character "pulsing"), grounded in the correct assumption (static camera) rather than blanket smoothing.
4. **Hold-and-fade instead of full-shape interpolation across hand-detection gaps** — a documented, measured decision (reported ~4.5x mean jerk reduction) rather than an assumed improvement.
5. **Discovering and documenting the 3-signer composition of the ZHO dictionary**, and recommending single-signer selection for Episode 1 to preserve presenter consistency — a real linguistic/production-quality insight most implementers would miss.
6. **Explicitly avoiding the newer MediaPipe pip release** after finding a real native crash, pinning to a working version with the reason documented in-code — reproducible, not just "it didn't work, tried something else."
7. **Explicitly dropping headwear/costume detail** from the avatar rather than shipping a broken/uncanny version — a real, stated scope-discipline decision (per code comments) favoring a working simple result over an unfinished elaborate one.
8. **Deferring the rigged-art avatar rather than shipping it half-working** — the fallback (procedural renderer) is clearly marked as the safe default, and the rigged track's known bug (hand orientation) is documented rather than hidden.

---

# 26. Weaknesses / Risks

| Risk | Rating | Notes / Mitigation |
|---|---|---|
| STRUCTURE/GENERATE/VALIDATE pipeline code doesn't exist; UNDERSTAND exists but isn't wired to anything | **HIGH** | UNDERSTAND is now real and proven (the LLM benchmark), but nothing converts its extracted concepts into a structured lesson, matches them to signs, or validates the result. Mitigation: this must be built before any panel demo — even a minimal version connecting benchmark output → sign selection. |
| ~~No LLM benchmark evidence present in-repo~~ RESOLVED | — | Recovered and relocated into `benchmarks/` on 2026-08-21; numbers verified to match project memory. No longer a risk. |
| Limited/mismatched sign vocabulary for Episode 1 | **HIGH** | Only 1/24 required science terms have a direct ZHO match (per `coverage_report.md`); the rest need fingerspelling, which is unglossed and not linguistically equivalent to a real sign. Mitigation: the coverage report already frames this honestly — keep that framing, don't overclaim vocabulary breadth. |
| No cross-signer standardization | **MEDIUM** | Mitigated in practice by the "use one signer only" recommendation, which sidesteps rather than solves the problem — fine for a single-episode prototype, would need real work to scale. |
| Sign-language linguistic accuracy unvalidated | **HIGH** | No sign-language expert review exists in-repo or is referenced as completed. All "signs" are literal word lookups/fingerspelling with no grammar/ordering logic. Mitigation: state this explicitly as a known limitation, per the brief's own instruction (§7) to surface limitations rather than hide them. |
| Lack of facial/non-manual markers | **MEDIUM** | Some real facial expressiveness exists (mouth curvature, eye width) but it is generic expression mimicry, not ASL/ArSL-specific non-manual grammar markers (which carry real linguistic meaning in sign languages, e.g. eyebrow raise for yes/no questions). Mitigation: be precise that this is "expressive avatar," not "linguistically correct non-manual grammar." |
| Keypoint jitter | **LOW** | Actively and measurably mitigated via EMA smoothing; residual risk only in edge cases (fast motion, occlusion) not stress-tested here. |
| Unnatural inter-sign transitions | **MEDIUM** | Crossfade dissolve, not pose-aware blending (see §13) — visually softens cuts but doesn't produce continuous, natural sign-to-sign motion. |
| Avatar hand fidelity | **LOW–MEDIUM** | Real per-finger tracking is a genuine strength; known unresolved gap is hand-near-face overlap clutter (explicitly flagged, not solved, in the handoff doc). |
| Unsupported terminology / fingerspell fallback | **HIGH** | No fingerspell-sequence generation code exists in this repo at all (only the raw Alphabets clip set was downloaded) — the fallback mechanism described in the brief is not implemented. |
| Source-grounding gaps | **HIGH** | No code connects the source text to any output at all (see §4) — this is currently a complete gap, not a partial one. |
| No `.git` history / no dependency lockfile | **MEDIUM** | Makes reproducibility and change-tracking impossible for a panel review; recommend at minimum a `pyproject.toml`/`requirements.txt` before presenting, and ideally initializing version control. |

---

# 27. Requirement Coverage Matrix

| Requirement | Implemented? | Evidence/file | Quality | Remaining gap |
|---|---|---|---|---|
| Solution architecture defined | Yes (doc only) | `Brief/AI-Powered Sign Language Academic Video Generator.md` | Clear, detailed | Not yet reflected in a working codebase beyond stages 1 and 6 |
| Role of AI clearly scoped | Yes | Brief §0–§1, `benchmarks/llm_grounding/` | Good design intent, now backed by a working local LLM stage | LLM stage not yet wired to downstream STRUCTURE/GENERATE |
| Model selection / local deployment | Yes | `benchmarks/llm_grounding/results/ch3_benchmark_results_v3_FINAL.log`, `benchmarks/alyah/results/alyah_eval_FINAL.log`, `benchmarks/README.md` | Real, reproducible, multi-metric, honest about the one failing model | Latency/throughput numbers not captured in these artifacts |
| Content understanding | Partial | `benchmarks/llm_grounding/run_ch3_benchmark.py` | Real concept/term/source-span extraction proven on actual source text | Only extraction is implemented; no summarization/lesson-structuring beyond that |
| Sign-language generation | No | — | — | Entirely unimplemented (only playback of pre-selected clips exists) |
| Performance/evaluation | Partial | `data/zho/coverage_report.md` | Real, rigorous for what it covers | Covers vocabulary indexing only, not model or sign-language quality |
| Security/data handling | Partial | `.env` (hf_token) | No obvious mishandling found | No `.gitignore`/no git repo at all to enforce secret hygiene going forward |
| Source verification/data quality | Partial | `coverage_report.md`, `content/grade6_science_ch3_cells.md` (explicitly labeled non-official stand-in) | Honest about limitations | No pipeline connects the verified source to any output |
| Deployment/scalability | Minimal | Ad hoc `.venv`s, no lockfile | Working locally for the developer | No documented/reproducible deployment path |
| Complete prototype episode | No | — | — | No Episode 1 (Cells) video exists; only a general-vocabulary demo reel |
| Source traceability | No | — | — | No traceability mechanism implemented in-repo |
| README | Not found | — | — | No top-level README exists in this repository |
| Source code | Partial | `scripts/`, `data/zho/` | Real, working for stages 1 & 6 | Stages 2–5 (understand/structure/generate/validate) have zero code |

---

# 28. Production Path

**Phase 1 – improve current prototype:**
- Build the missing UNDERSTAND/STRUCTURE/GENERATE/VALIDATE stages as actual code (even minimal versions), wired to `content/grade6_science_ch3_cells.md`.
- Bring the LLM benchmark script and raw results into this repository so they're reproducible and reviewable.
- Implement a real gloss/fingerspell-generation step with confidence flagging, replacing the current hand-picked demo word list.
- Add a `requirements.txt`/`pyproject.toml` and a README.

**Phase 2 – validated sign-language system:**
- Get real sign-language expert review of generated gloss sequences and fingerspelling output.
- Solve or formally scope-limit the cross-signer/standardization problem if more than one signer's data is ever mixed.
- Replace crossfade-only sign transitions with pose-aware blending.
- Expand facial animation toward real non-manual grammar markers, with linguistic guidance.

**Phase 3 – production deployment:**
- Batch/parallelize MediaPipe extraction and cache per-sign motion data instead of recomputing per lesson.
- Formalize the human-in-the-loop validation stage as an actual reviewable UI/workflow.
- Establish real curriculum sourcing (replacing the explicitly-labeled prototype stand-in text) and a real source-to-output traceability audit trail.

---

# 29. Panel Questions I Should Expect

1. **"Show me the code that turns the science text into a sign sequence."** → It doesn't exist yet in this repo; be upfront that stages 2–5 of the pipeline are still to be built, and describe the planned design from the brief.
2. **"What were your actual LLM benchmark numbers?"** → Falcon-H1-7B wins on every metric the brief names (cosine 0.908, ROUGE-1 0.755, ROUGE-L 0.734, Jaccard 0.664, BLEU 0.597); raw extractions and scored logs are in `benchmarks/llm_grounding/results/`. Be ready to also explain why jais-adaptive-7B failed (JSON-formatting quirk + a real content-complexity ceiling on dense sections) — a stronger answer than a clean sweep would be.
3. **"Is this Arabic Sign Language or just word-for-word fingerspelling?"** → Currently the pipeline has no gloss/grammar logic at all; today's demo is a raw-vocabulary playback, not a linguistically structured translation.
4. **"How many of your Episode 1 terms actually have real signs?"** → 1 of 24 direct matches per your own coverage report — be ready to explain the fingerspelling-fallback plan for the rest, and that the fallback isn't code-implemented yet.
5. **"Is this Emirati Sign Language specifically, or standard Arabic Sign Language?"** → ZHO is the UAE's own dictionary (a strong, defensible source), but MoE HR clarified standard ArSL is acceptable too — cite that clarification rather than overclaiming ZHO exclusivity.
6. **"How do you handle signs you don't have in your dictionary?"** → Currently: no automated handling exists; only the raw Alphabets clip set is downloaded, with no fingerspell-sequencing code built yet.
7. **"Who are the people signing in your dictionary, and does that matter?"** → 3 distinct signers identified; explain the presenter-consistency finding and the "use one signer" mitigation.
8. **"Why not just use the highest-coverage signer for everything?"** → Because Signer B, despite covering 92.9% of the dictionary, isn't used for Episode 1's one direct match, to preserve a single consistent presenter — explain this deliberate trade-off.
9. **"How do you know your source text is the right/approved content?"** → It explicitly isn't — the file is a labeled stand-in; be upfront that real curriculum sourcing is a Phase 3 item.
10. **"What guarantees that your output doesn't hallucinate facts?"** → None currently, because no LLM-driven generation runs on the source text in this repo at all; describe the intended grounding approach from the brief as a plan, not a result.
11. **"Where is your validation/review UI?"** → Doesn't exist; describe it as a planned human-in-the-loop gate per the brief, not yet implemented.
12. **"How fast is your pipeline end-to-end?"** → No end-to-end pipeline exists to time; only MediaPipe extraction (~30fps on M1 Pro) is independently measurable.
13. **"Is this running fully locally, satisfying the no-external-API constraint?"** → The MediaPipe/avatar path is fully local; there's no LLM inference code in this repo to make a local-vs-cloud claim about either way.
14. **"Why 2D flat-shape avatar instead of a 3D rig?"** → Explain it as a deliberate scoping decision (stated in the script's own docstring) — a real, known ceiling versus 3D, chosen for reliability and speed of iteration.
15. **"Why didn't the rigged Emirati-costume avatar make it into the final version?"** → Real, documented blocker: source-art quality issues and an unfixed hand-orientation bug — explain it as an honest engineering trade-off, not abandoned carelessly.
16. **"Do your hand animations reflect real finger articulation or are they simplified?"** → Real, per-frame MediaPipe-driven finger tracking in the procedural renderer — this is a genuine strength, be specific about it.
17. **"What happens when the hand overlaps the face?"** → Known, explicitly flagged unfixed limitation (partial halo mitigation only) — don't claim it's solved.
18. **"How do you smooth out noisy tracking data?"** → EMA smoothing per channel, with specific alpha values and a documented rationale — a strong, concrete answer.
19. **"How do you keep the avatar's size consistent across a clip?"** → Fixed per-clip scale computed once (median shoulder width), explain the pulsing artifact it fixes.
20. **"How do transitions between signs work — are they natural?"** → Currently a video crossfade dissolve, not pose-continuous blending; be honest this is a visual smoothing trick, not true motion continuity.
21. **"Can this scale to a full curriculum, not just one episode?"** → Not without caching/batching work and, most importantly, building the missing middle pipeline stages — be specific about what Phase 1–3 would require.
22. **"Is there any security risk in your repo (API keys, tokens)?"** → One HF token in `.env`, not read by any script found; flag it for `.gitignore` treatment before version-controlling this repo.
23. **"Why is there no requirements file or lockfile?"** → Fair gap; commit to adding one (`uv`-based per your own project convention) before the panel review.
24. **"What's the single biggest technical risk in this prototype?"** → The complete absence of the understand/structure/generate/validate pipeline — the "AI" core of the AI-powered claim.
25. **"What's the strongest, most defensible piece of engineering here?"** → The ZHO indexing/coverage work and the keypoint-smoothing/gap-holding logic — both are real, measured, and honestly self-documented rather than asserted.
26. **"How do you know your MediaPipe extraction is accurate enough for sign language specifically (not just generic pose estimation)?"** → Cite the reasoning behind choosing MediaPipe over YOLO-pose (dedicated hand model, more accurate per external research) — but note no in-repo ground-truth accuracy evaluation exists.
27. **"If a term isn't fingerspell-able either (e.g., no letter clip available), what happens?"** → No handling exists in code; would need to design and implement an explicit "flag as unsupported" path.

---

# 30. Facts I Must NOT Overclaim

- "This system generates Arabic Sign Language from academic text" — it does not; no code connects source text to sign output.
- ~~"We benchmarked and selected the best local LLM"~~ — this claim IS now supportable: `benchmarks/llm_grounding/` proves it with real, reproducible numbers. Do not, however, claim the benchmark's extraction output is currently *used* by anything downstream — it isn't wired into a pipeline yet.
- "Our avatar is driven by a fully standardized multi-signer pipeline" — standardization exists only within a single clip/segment, not across different human signers; the actual mitigation used is avoiding signer-mixing, not solving it.
- "The system flags unsupported vocabulary automatically" — no such logic exists in code.
- "This is a validated/expert-reviewed sign language system" — no expert review or validation code/artifact exists in-repo.
- "The prototype demonstrates a full academic episode in sign language" — the existing videos are a general-vocabulary demo reel, not Episode 1 content.
- "The avatar accurately reproduces the full 543-point MediaPipe Holistic output" — it uses a reduced subset (8 pose points, full hand joints, ~18 derived face metrics), not the full landmark set.
- "The facial animation conveys correct ASL/ArSL non-manual grammar" — it conveys generic expressiveness (smile/brow/eye-width), not linguistically validated grammatical markers.
- "Source traceability is built in" — no traceability code exists connecting any output back to `content/grade6_science_ch3_cells.md`.
- "Sign transitions are naturally blended" — they are video crossfades, not pose-continuous motion blending.

---

# 31. Final Technical Assessment

- **Prototype maturity: 3/10.** Two of six intended pipeline stages exist and work well in isolation (vocabulary ingestion, avatar rendering); the three stages that constitute the "AI-powered" core of the case study (understand, structure, generate) and the validation stage do not exist as code anywhere in this repository. No end-to-end run is currently possible.
- **AI/content pipeline: 4/10.** The LLM extraction stage itself is genuinely strong (real benchmark, real winner, real debugging story) — but it's a standalone script, not a pipeline: nothing calls it automatically, and its output doesn't feed a STRUCTURE or GENERATE stage that also don't exist. Score reflects one solid, isolated piece rather than a working chain.
- **Sign-language pipeline: 2/10.** Real, high-quality vocabulary data exists (ZHO catalog, coverage analysis), but there is no gloss-generation, matching, ordering, or fingerspell-sequencing logic — the "pipeline" is currently just a dictionary plus a renderer, with no connective logic between them.
- **Avatar/rendering: 7/10.** The strongest subsystem in the repo — real MediaPipe-driven finger/body/face animation, measured and documented fixes for real artifacts (jitter, scale pulsing, uncanny hand-morphing). Held back from higher only by simplified clothing/face detail, unfinished rigged-art track, and video-crossfade-only transitions.
- **Source-grounding: 0/10.** No code path connects the academic source text to any generated output whatsoever in this repository.
- **Evaluation quality: 2/10.** One real, rigorous evaluation exists (ZHO coverage report) but it measures vocabulary coverage, not model quality or sign-language correctness — the required grounding-faithfulness benchmark and any sign-language-quality evaluation are entirely absent from this repo.
- **Readiness for the case-study panel: 5/10, as this repository currently stands.** The panel can now be shown real, reproducible benchmark evidence for model selection alongside the ZHO indexing and avatar engineering — three genuinely defensible pieces of work. What's still missing is the connective tissue: STRUCTURE, GENERATE, VALIDATE, and any wiring that makes UNDERSTAND's output actually drive SIGN VIDEO. A confident defense of "what we built and why" is very achievable for the pieces that exist; a live demo of the full case study end-to-end is not yet possible.

---

# QUICK HANDOFF TO CHATGPT

**Project:** UAE MoE AI Center of Excellence candidate case study — "AI-Powered Sign Language Academic Video Generator." Prototype must transform one academic lesson (Grade 6 Science, Ch.3, "Cells") into an Arabic Sign Language video, with LOCAL-ONLY core inference, source-grounding/traceability, and human-in-the-loop validation.

**Current architecture (as actually built, not as designed):** SOURCE (ZHO dictionary indexing — done) → UNDERSTAND (LLM grounding-extraction benchmark — done and proven on real source text, but runs as a standalone script, not wired to anything downstream) → STRUCTURE/GENERATE/VALIDATE (**not implemented, zero code in this repo**) → SIGN VIDEO (avatar rendering from pre-selected demo words — done, but not driven by the academic content or by UNDERSTAND's output). There is no wiring connecting UNDERSTAND's extracted concepts to the rendered output.

**Models tested + metrics (VERIFIED FROM OUTPUT-ARTIFACT, `benchmarks/`):** Qwen3-8B, Qwen3.5-9B, Falcon-H1-7B-Instruct, jais-adaptive-7B — grounding-faithfulness benchmark on real Ch.3 source text (cosine/ROUGE-1/ROUGE-L/Jaccard/BLEU/source-span-match), plus a supplementary 1,173-question TII Alyah Emirati-dialect benchmark. **Chosen model: Falcon-H1-7B-Instruct** — wins every metric the brief names (cosine 0.908, ROUGE-1 0.755, ROUGE-L 0.734, Jaccard 0.664, BLEU 0.597) and the Alyah eval (64.88% accuracy). jais-adaptive-7B fails to produce valid JSON in a single pass; root-caused to a formatting quirk plus a genuine content-complexity ceiling on dense sections. All results in `benchmarks/llm_grounding/results/` and `benchmarks/alyah/results/`, methodology in `benchmarks/README.md`.

**Sign vocabulary size:** 1,143 total ZHO dictionary entries indexed (`data/zho/catalog.json`), only 36 clips actually downloaded (Alphabets + Directions-and-Locations categories). Episode 1's 24-term science vocabulary has only 1 direct dictionary match — everything else needs fingerspelling (not yet implemented as code).

**Number of signers:** 3 distinct people identified in the ZHO dictionary by visual inspection (Signer A: female, Alphabets only, 35 entries; Signer B: male, 92.9% of the dictionary; Signer C: male, Sports category only). Recommendation on record: use Signer A only for Episode 1 to keep the presenter consistent.

**MediaPipe pipeline:** `mp.solutions.holistic.Holistic` (legacy API, pinned to `mediapipe==0.10.14` due to a crash in the newer 1.0.1 release), CPU-only, ~30fps on M1 Pro. Extracts 8 pose points, 21 landmarks per hand, and 6 derived face-expression scalars (mouth open/width, eye open/width, brow raise, smile) from a curated FaceMesh subset. EMA-smoothed per channel (alpha 0.25 pose/face, 0.3 hands).

**Normalization method:** fixed per-clip scale (median shoulder width across the clip, computed once, not per-frame) to avoid visible size-pulsing from landmark noise; hand size separately normalized per-frame to a fixed target span. No cross-signer normalization exists — mitigated only by not mixing signers.

**Motion JSON structure:** `{fps, width, height, frames: [{frame, pose: {l_sh, r_sh, l_el, r_el, l_wr, r_wr, l_hip, r_hip: [x,y,z]}, left_hand: [[x,y,z]×21] or null, right_hand: ..., face: {mouth_open, mouth_width, eye_open, eye_width, brow_raise, smile}}]}`. A multi-segment lesson variant wraps 29 of these under a top-level `segments` list, each with its own `stem`/`english`/`arabic` labels.

**Avatar/rendering approach:** primary working renderer is a 2D flat-shape/vector renderer using OpenCV (capsule limbs, filled-polygon robe, per-finger capsule chains driven directly by tracked hand landmarks, curved-mouth face). A second, unfinished track drives real character art via PIL affine transforms per limb, blocked by a known unfixed hand-orientation bug and poor source-art quality.

**Prototype status:** working demo reel of 29 general ZHO vocabulary words (not Episode 1 content) rendered with real tracked motion, English+Arabic captions, ffmpeg crossfades between segments. No academic-content-driven video exists yet.

**Working commands:** `python3 scripts/zho_index.py`, `python3 scripts/zho_download.py`, `uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python --with numpy python3 scripts/spike_cartoon_avatar.py` (single clip). No command exists that goes from source text to sign video.

**Major limitations:** UNDERSTAND stage exists but isn't wired to anything (STRUCTURE/GENERATE/VALIDATE are entirely unimplemented); no source-grounding/traceability mechanism connecting UNDERSTAND's output to any final artifact; no validation/review workflow; only 1/24 Episode 1 terms have direct sign matches; no fingerspell-sequence generation code; transitions between signs are video crossfades, not pose-continuous blends; no cross-signer standardization; no requirements/lockfile or README in the repo; not under version control.

**Strongest evidence in-repo:** `benchmarks/llm_grounding/results/ch3_benchmark_results_v3_FINAL.log` (real, reproducible, multi-metric LLM benchmark on actual source text, with an honestly-debugged failure case), `data/zho/coverage_report.md` (rigorous, honest vocabulary/signer analysis with real numbers), and `scripts/spike_cartoon_avatar.py` (real, measured, well-documented MediaPipe-driven avatar rendering with genuine bug-fixes, e.g. gap-hold vs. interpolation, jerk-reduction measurement).

**Top 5 files to inspect next:**
1. `Brief/AI-Powered Sign Language Academic Video Generator.md` — the full intended design/build order.
2. `benchmarks/README.md` — LLM benchmark methodology, final numbers, and rerun instructions for both evals.
3. `data/zho/coverage_report.md` — real vocabulary/signer findings, ground truth for what's actually available.
4. `scripts/spike_cartoon_avatar.py` — the working avatar rendering core, most substantial rendering code in the repo.
5. `data/zho/spike_mediapipe/AVATAR_HANDOFF.md` — status/next-steps doc for the avatar side-track, including the unresolved rigged-renderer bug.
