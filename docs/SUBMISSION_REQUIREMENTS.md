# Submission Requirements Compliance Matrix

Source of truth for the brief: `MOI-Task/Case Study 3 - AI-Powered Sign Language Academic Video Generator.pdf` ("AI-Powered Sign Language Academic Video Generator", UAE MoE AI Center of Excellence). Note: the brief's "Episode 1: Cells" mock-up is explicitly labeled *"Illustrative concept only · not the UI candidates are expected to reproduce"* — Cells is one worked example in the brief, not a mandated hero topic. This matrix does not treat Cells as required.

Legend: **IMPLEMENTED** = working in this prototype today, with evidence. **PRODUCTION DESIGN / NEXT STEP** = designed/argued for, not built in the two-week prototype.

## Deliverables (brief page 2)

| Requirement | What we built | Evidence | Where to demonstrate | Status |
|---|---|---|---|---|
| Working prototype, end-to-end functioning demo | CLI (`run_pipeline.py`) + FastAPI/React webapp, both driving the same `lib/pipeline_runner.py` | ~50 completed jobs under `outputs/webapp_jobs/*/final_episode.mp4`, plus named runs (`outputs/eval_h`, `outputs/gate_check_*`, etc.) | Live webapp at `localhost:5173`, or any `outputs/*/final_episode.mp4` | IMPLEMENTED |
| Max 4 slides | Slide content drafted | `docs/SLIDE_CONTENT.md` | — | Content ready; PPTX design itself intentionally not produced per task constraints |
| Source code | Git repo, branch `feature/bilingual-zho-resolution` | `git log`, `lib/`, `webapp/`, `scripts/` | This repo | IMPLEMENTED |
| Short README | `README.md` (18 sections, architecture/run/limits/production path) | `/Users/shaz/MOI-Arabic-Sign-Language/README.md` | Repo root | IMPLEMENTED — see README status note below (contains local absolute-path-free content but references dev history; see hygiene audit for trim recommendation before final submission) |

## SOURCE → UNDERSTAND → STRUCTURE → GENERATE → VALIDATE → SIGN VIDEO (brief's own pipeline)

| Stage | What we built | Evidence | Status |
|---|---|---|---|
| SOURCE | Hashed `.md`/`.txt` ingestion, EN or AR, `lib/source_loader.py` | `source_manifest.json` per job (hash, path, language, timestamp) | IMPLEMENTED |
| UNDERSTAND | Local Falcon-H1-7B (via Ollama) grounded concept extraction + deterministic source-span verification | `lib/understand.py`; `understanding.json` per job | IMPLEMENTED |
| STRUCTURE | Episode Builder turns verified concepts into short educational sentences; semantic sign-plan decomposition (meaning, not word list) | `lib/episode_builder.py`, `lib/sign_plan.py`; `episode.json` | IMPLEMENTED |
| GENERATE (sign resolution + rendering) | Deterministic match against 1,143-entry ZHO catalog → ESL Zayed supplementary → Arabic-fingerspelling fallback; MediaPipe-driven procedural avatar renderer | `lib/sign_resolver.py`, `lib/fingerspell.py`, `scripts/spike_cartoon_avatar.py`; `segments/*.mp4` | IMPLEMENTED |
| VALIDATE | Deterministic provenance/coverage checks; can BLOCK rendering; two-track human review (academic vs sign-language) | `lib/validator.py`; `validation.json`, `review_required.md` | IMPLEMENTED |
| SIGN VIDEO | ffmpeg crossfade-assembled final episode with Arabic captions | `final_episode.mp4` per job | IMPLEMENTED |

## Arabic Sign Language requirements (brief)

| Requirement | Status | Evidence / Limitation |
|---|---|---|
| Primary target language for output | IMPLEMENTED | All final videos are ASL segment sequences with Arabic captions |
| Preserve educational meaning, not literal word-for-word | IMPLEMENTED | `lib/sign_plan.py` decomposes sentences into semantic items (entities/actions/relations), not key-word lists; README §6 |
| Consider terminology, vocabulary limits, uncertain translations; flag rather than hide | IMPLEMENTED | Every resolution labeled `VERIFIED_SIGN`/`FINGERSPELL_CANDIDATE`/`UNSUPPORTED`/`REVIEW_REQUIRED`; two separate coverage numbers (`verified_lexical_sign_coverage_pct`, `renderable_coverage_with_fallback_pct`) never conflated — README §7 |
| Propose and justify own fallback approach | IMPLEMENTED | Deterministic Arabic fingerspelling via `arabic_alphabet_map.json` (35-entry verified ZHO alphabet set) when no verified lexical sign exists; justified in README §7/§9 | 

## Local AI models only

| Requirement | Status | Evidence |
|---|---|---|
| Core inference (understanding, transformation, sign generation) runs locally | IMPLEMENTED | Falcon-H1-7B-Instruct served via local Ollama; sign resolution/fingerspelling are deterministic (no model call at all) — see security audit for exact grep evidence of no external generative-AI calls |
| External generative AI APIs must not perform core stages | IMPLEMENTED | No cloud LLM/embedding API calls found in `lib/` or `webapp/backend` (see security audit) |
| Explain model family, size, hardware, performance, local-deployment rationale | IMPLEMENTED | README §3 (benchmark table across 4 local Ollama models), §10 (install/hardware); `benchmarks/llm_grounding/` |

## Source grounding (brief's explicit key requirement)

| Requirement | Status | Evidence |
|---|---|---|
| Must not introduce facts not traceable to approved source | IMPLEMENTED | `understanding.json` carries `source_span_verified` flags; deterministic vocabulary-overlap grounding check (README §14 — described honestly as "a crude heuristic, not a factuality prover") |
| Every generated episode traceable to its source | IMPLEMENTED | `traceability.json`/`traceability.md` per job, chain: source span → concept → realization → resolution → selected sign → authority → source id → rendered segment → final video (see `docs/TRACEABILITY_EXAMPLES.md`) |

## "How Would You Build It?" — the 5 discussion areas

| Area | Status | Where documented |
|---|---|---|
| 01 Solution Architecture | IMPLEMENTED + documented | README §2, `docs/SLIDE_CONTENT.md` Slide 2 |
| 02 Role of AI (AI vs deterministic, human-in-the-loop) | IMPLEMENTED + documented | README §6–§8; `docs/PANEL_DEFENSE.md` |
| 03 Model Selection & Local Deployment | IMPLEMENTED + documented | README §3, `benchmarks/llm_grounding/` |
| 04 Content Understanding | IMPLEMENTED | `lib/understand.py`, `lib/episode_builder.py` |
| 05 Sign-Language Generation | IMPLEMENTED | `lib/sign_plan.py`, `lib/sign_resolver.py`, `lib/fingerspell.py` |

## "Also be prepared to discuss"

| Area | Status | Where documented |
|---|---|---|
| Performance & Evaluation | PARTIALLY IMPLEMENTED (benchmarks exist; formal accuracy/latency dashboards do not) | `benchmarks/llm_grounding/results/*.log`, regression tests in `tests/` |
| Security & Data Handling | IMPLEMENTED (local-first, documented gaps) | README §16; `docs/SECURITY_AND_HYGIENE_AUDIT.md` |
| Source Verification & Data Quality | IMPLEMENTED (ZHO) / DOCUMENTED LIMITATION (ESL Zayed provenance) | `data/zho/coverage_report.md`, `data/zho/catalog_validation_report.json` |
| Deployment & Scalability | PRODUCTION DESIGN / NEXT STEP (current prototype is single-threaded, no queueing, no auth, no DB) | README §17, §18 "Prototype limitations (web app specifically)" |

## Additional technical areas (per task brief scope)

| Area | Status | Note |
|---|---|---|
| Terminology handling | IMPLEMENTED | `lib/terminology.py` — one contextual Falcon-proposed MSA term per unresolved item, deterministically sanity-checked |
| Vocabulary limits | IMPLEMENTED / documented limitation | ZHO is general-vocabulary; 1/24 direct term matches for the Cells science episode (documented, not hidden) |
| Uncertain translations | IMPLEMENTED | `REVIEW_REQUIRED` status, never silently upgraded |
| Fallback | IMPLEMENTED | Fingerspelling, explicitly labeled, never presented as a verified sign |
| Hallucination prevention | IMPLEMENTED (architectural, not a proof of impossibility) | See `docs/SLIDE_CONTENT.md` Slide 3 and PANEL_DEFENSE.md |
| Traceability | IMPLEMENTED | Per-job `traceability.json`/`.md` |
| Evaluation | PARTIAL | Grounding benchmark + regression tests exist; no held-out human sign-language accuracy evaluation (requires a qualified interpreter — NEXT STEP) |
| Human-in-the-loop | IMPLEMENTED at flag/status level; PRODUCTION DESIGN for actual human reviewer workflow/UI | `review_required.md`; no reviewer login/approval UI exists |
| Deployment/scalability | PRODUCTION DESIGN / NEXT STEP | See README §17 and Deployment section below |

## Honest gaps (do not fabricate coverage of these)

- No qualified Arabic Sign Language linguist has reviewed any output (README §8, stated directly).
- No production reviewer UI/workflow — review status is file-based (`review_required.md`), not an interactive approval screen.
- No formal latency/throughput benchmark of the end-to-end pipeline (stage timings are captured per job in `stage_timings.json` but not aggregated/reported as an SLA).
- No automated accessibility audit of the webapp (`docs/FEDERAL_VISUAL_IDENTITY.md` §11 flags this explicitly).
