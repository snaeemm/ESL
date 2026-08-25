# Slide Content (4 slides max, per brief) — content only, no PPTX

## Slide 1 — Proof of a working prototype

- Hero lesson: **"A Day With My Family (Part 2)"** (`content/test_h2_showcase_part2.md`), job `outputs/webapp_jobs/bdff1892c9da/`
- [Screenshot slot: Results screen, Lesson tab, video playing]
- [Screenshot slot: final frame still from `final_episode.mp4`]
- Statement: "All core AI inference (understanding, semantic planning) runs locally — Falcon-H1-7B-Instruct via Ollama. No cloud generative-AI API is used for any core stage."
- Link: "Watch demo" → standalone recording per `docs/DEMO_VIDEO_PLAN.md`, or live webapp at presentation.
- One line: 91-second video, 20 rendered segments, real traceability for every one.

## Slide 2 — Architecture

- Pipeline diagram: **SOURCE → UNDERSTAND → STRUCTURE → GENERATE → VALIDATE → SIGN VIDEO** (matches brief's own diagram exactly)
- AI vs deterministic boundary, one line each:
  - SOURCE: deterministic (hash + language detect)
  - UNDERSTAND: **AI** (Falcon) + deterministic source-span verification
  - STRUCTURE: **AI** (Falcon sentence/semantic-plan generation)
  - GENERATE (sign resolution): **deterministic** (catalog match, no model call for the final asset choice)
  - VALIDATE: **deterministic** (coverage/provenance rules, can BLOCK)
  - SIGN VIDEO: **deterministic** (MediaPipe-driven procedural rendering + ffmpeg assembly)
- Model choices: Falcon-H1-7B-Instruct (Q4_K_M, local Ollama) for language understanding/semantic planning; multilingual-MiniLM-L12-v2 embeddings for bilingual candidate retrieval (Recall@1 0.733, Recall@5 0.933 on a 30-pair bilingual synonym benchmark, beating e5-small and lexical-only baselines — `data/zho/spike_mediapipe/ab_experiment_20260823/FINAL_REPORT.md`).

## Slide 3 — Sign-authority hierarchy

- **ZHO (institutional, primary)** → **ESL Zayed (supplementary, observed)** → **Fingerspell / Review (fallback)**
- ESL Zayed never overrides an existing ZHO sign, and its coverage is never blended into the institutional coverage number.
- One traceability example (from `docs/TRACEABILITY_EXAMPLES.md`, job `bdff1892c9da`, unit u03 "Academic Success"): `I` → ESL Zayed, `EXAM`/`FAMILY` → ZHO, `DO WELL`/`IS PROUD` → fingerspell, `ON` → honestly flagged UNSUPPORTED (unmapped Arabic letter ى) — all six outcomes in one sentence.
- 2–4 strongest real metrics: 1,143 ZHO entries / 244 ESL Zayed supplementary entries; Falcon-H1 wins grounding benchmark on every metric (0.908 cosine, 85.7% source-span match) vs 3 other local models; 77/77 automated regression tests passing.
- Message: **"The LLM does not get to invent sign authority."** Falcon proposes semantic meaning only; a deterministic resolver decides the actual sign against fixed, verified catalogs.

## Slide 4 — Performance, security, deployment, limitations, roadmap

- Performance/eval: Falcon-H1 benchmark (`benchmarks/llm_grounding/`), 77 passing regression tests (`tests/`), real per-job coverage numbers (never a single blended figure).
- Security/data handling: core inference local-only (Ollama); no secrets in repo; only outbound network calls are one-time ZHO/ESL Zayed source-clip downloads, not the runtime inference path.
- Source verification/data quality: ZHO validated (1,143/1,143 rows, 0 missing video assets, 6 entries with disclosed missing Arabic labels — preserved as missing, not fabricated); ESL Zayed explicitly tagged `SUPPLEMENTARY_UNVERIFIED` in every catalog entry.
- Deployment/scalability status: **prototype today** = single-thread job worker, in-memory job manager, no DB, no auth, sequential clip processing with ID-level caching. **Production path** (NOT yet implemented) = GPU-served models, precomputed motion cache, batch generation queue, model/version registry, audit logging, monitoring, curated/expert-validated vocabulary.
- Human-in-the-loop: two-track review (academic meaning vs sign-language linguistic correctness) via `review_required.md`; `BLOCKED` always stops rendering; `REVIEW_REQUIRED` never silently upgraded.
- Honest limitations: not linguistically validated by a certified ASL expert; ZHO alone has near-zero science-domain coverage; crossfade transitions, not pose-blended motion; grounding check is a vocabulary-overlap heuristic, not a factuality prover.
- Production roadmap: Phase 1 (harden grounding + caching) → Phase 2 (expert linguistic validation + licensed corpus) → Phase 3 (GPU serving, batch, registry, monitoring).
