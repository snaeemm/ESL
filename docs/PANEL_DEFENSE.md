# Panel Defense — Evidence-Backed Q&A

All answers reference real repo artifacts. Where the prototype has a limitation, it is stated as a limitation, not glossed over.

**1. Why this architecture (SOURCE→UNDERSTAND→STRUCTURE→GENERATE→VALIDATE→SIGN VIDEO)?**
Matches the brief's own pipeline exactly. Each stage writes a JSON artifact (`outputs/<run>/*.json`), so every stage is independently inspectable and the pipeline is auditable rather than a black box. See README §2.

**2. Why Falcon?**
`benchmarks/llm_grounding/` ran a grounding-faithfulness benchmark (cosine similarity, ROUGE-1/L, Jaccard, BLEU, source-span verbatim match) on real Cells source text across 4 local Ollama models. Falcon-H1-7B-Instruct won every metric the brief cares about (0.908 cosine, 0.755 ROUGE-1, 85.7% source-span match, valid JSON). Qwen3.5-9B and Qwen3-8B were weaker; jais-adaptive-7B failed to produce valid JSON at all. README §3, `benchmarks/llm_grounding/results/ch3_benchmark_results_v3_FINAL.log`.

**3. Why local AI (not a cloud LLM)?**
Brief mandates it: "external generative AI APIs must not perform these core stages." Practically: data governance (curriculum content stays on-premises), reproducibility (pinned model weight vs a cloud endpoint that can change), and cost/latency control at scale.

**4. What model/config exactly?**
`hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, served via Ollama (README §10 install command). 7B parameters, 4-bit quantized (Q4_K_M).

**5. Hardware / performance?**
Prototype developed and measured on Apple M1 Pro (CPU-only for MediaPipe: ~30fps, measured, per script docstring). Falcon-H1-7B Q4_K_M inference latency per job is captured in `stage_timings.json` per run but not yet aggregated into an SLA figure — NEXT STEP.

**6. What do embeddings do here?**
They are configured for candidate retrieval in the bilingual ZHO-resolution work (`data/zho/catalog_embeddings_e5-small.npz`, `catalog_embeddings_minilm.npz`, `lib/vocab_embedding.py`/`vocab_embedding_st.py`). See `docs/DEMO_CANDIDATE_COMPARISON.md` / resolver findings for exact model identifiers and any benchmark numbers found in `data/zho/catalog_bilingual_report.json`.

**7. Why this embedding model (not another)?**
Selection is grounded in the same repo's bilingual ZHO resolver benchmarking work referenced in project memory; see `data/zho/catalog_bilingual_report.json` for the real comparison numbers actually produced during that work — reported precisely, not from memory alone.

**8. Why not let the LLM directly generate/pick signs?**
Because an LLM can hallucinate a sign that doesn't exist or misattribute authority. Sign selection is deterministic: Falcon proposes a *semantic* decomposition (meaning), then `lib/sign_resolver.py` matches that meaning against the verified ZHO/ESL Zayed catalogs with exact matching (no fuzzy substring matching that could silently change meaning, per `coverage_report.md`). The LLM never picks the final sign asset.

**9. What is ZHO?**
The UAE Zayed Higher Organization government sign-language dictionary — 1,143 catalog entries (`data/zho/catalog.json`), the institutional/primary sign authority in this system.

**10. Why is ZHO primary?**
It is the only government-verified sign-language lexical source used in this system; it therefore carries institutional authority that no other source in the pipeline is allowed to override.

**11. What is ESL Zayed?**
A supplementary, observed/researched sign source (video clips processed with MediaPipe, `data/zho/spike_mediapipe/esl_zayed_clips/`) used to fill vocabulary gaps ZHO's general-purpose dictionary doesn't cover. 244 catalog entries (`data/zho/esl_zayed_supplementary_catalog.json`).

**12. Why is ESL Zayed only supplementary, never institutional?**
It was not produced/verified by the government ZHO authority — it's an observed/derived educational source. The system therefore always labels it distinctly ("ESL Zayed (supplementary)" in the UI, `render_source: ESL_ZAYED`) and never lets it override an existing verified ZHO sign, and never reports its coverage blended into the institutional coverage number.

**13. How is hallucination prevented?**
Layered, not absolute: (a) Falcon proposes semantic decomposition only — it never outputs a final sign asset; (b) retrieval/matching against fixed, verified catalogs is deterministic; (c) `lib/validator.py` runs a separate deterministic provenance/coverage check that can BLOCK rendering; (d) anything unresolved is explicitly flagged (`UNSUPPORTED`/`REVIEW_REQUIRED`), never silently dropped; (e) traceability ties every rendered segment back to a source span. This reduces, not eliminates, the risk of a bad semantic decomposition — that's why sign-language linguist review remains a required, not optional, next step (README §8).

**14. How is meaning preserved (not word-for-word)?**
`lib/sign_plan.py` asks Falcon for a semantic item list (entities/actions/relationships), not a literal token-for-token gloss. Where Falcon can't produce a faithful breakdown, the unit is marked `REVIEW_REQUIRED` instead of guessed.

**15. How is missing vocabulary handled?**
Three-tier fallback: ZHO exact match → ESL Zayed supplementary exact match → deterministic Arabic fingerspelling via a static, documented 35-entry alphabet map. If none apply, `UNSUPPORTED`/`REVIEW_REQUIRED`, never invented.

**16. Why fingerspelling specifically (not a generated sign)?**
It's a real, teachable ASL fallback convention, fully deterministic (no model risk), and immediately explainable/traceable letter-by-letter — appropriate for a two-week prototype without a validated generative sign model.

**17. How does traceability actually work mechanically?**
`lib/traceability.py` walks each rendered segment and reconstructs: source span → concept → semantic realization → candidate/resolution → selected sign → authority (ZHO/ESL_ZAYED/FINGERSPELL) → source id (catalog id or video+timestamp) → rendered segment file → position in final video. Output as both `traceability.json` (machine) and `traceability.md` (human-readable), surfaced live in the webapp's Traceability tab.

**18. How do you prevent unsupported facts from appearing as if verified?**
Coverage is reported as two separate numbers — `verified_lexical_sign_coverage_pct` (ZHO only) vs `renderable_coverage_with_fallback_pct` (includes fingerspelling) — never blended, so a fingerspelled/fallback segment can never be mistaken for a verified sign in any report or UI.

**19. What is your evaluation methodology?**
Multiplemodel grounding-faithfulness benchmark for Falcon selection (`benchmarks/llm_grounding/`); regression test suite in `tests/` (resolver regressions, Arabic clitic normalization, avatar scale invariance, bilingual catalog behavior, ESL Zayed supplementary behavior, structured-output shape); real end-to-end job runs as functional evaluation. No held-out linguistic-accuracy evaluation by a certified interpreter yet — explicitly a next step, not claimed as done.

**20. What did you try and reject?**
jais-adaptive-7B rejected for source-grounding (0% source-span match, invalid JSON). YOLO-pose tested and rejected for the avatar pipeline (body-only, no hands/face, 5.2fps vs MediaPipe's 30fps on the same clip, measured). Fuzzy/substring vocabulary matching considered and explicitly rejected in `coverage_report.md` because it risks silently changing meaning.

**21. What are the known limitations?**
See README §14, verbatim: not linguistically validated ASL; ZHO alone doesn't cover science-domain vocabulary (1/24 direct matches for Cells); no cross-signer motion standardization; grounding check is a crude heuristic; semantic planning/terminology are LLM outputs, sanity-checked but not linguistically validated; sign transitions are crossfade dissolves, not pose-blended; no unlimited-vocabulary claim; no production-readiness claim.

**22. Where are the human-review checkpoints?**
Two tracks in `review_required.md`: ACADEMIC REVIEW (curriculum-meaning preservation, subject-matter teacher) and SIGN-LANGUAGE REVIEW (linguistic appropriateness, qualified ASL expert). A `BLOCKED` validation status always stops rendering; `REVIEW_REQUIRED` only renders with an explicit `--allow-review-render` flag and stays marked pending review. Additional future checkpoints: promotion of any ESL Zayed entry to institutional status; new curriculum-term additions; final pre-publish QA sign-off.

**23. Security & data handling?**
No secrets are read by pipeline code; the repo's own `.env` (a Hugging Face token, unrelated to this pipeline) is git-ignored. All core AI inference is local (Ollama). The only outbound network calls are to the public UAE ZHO government dictionary/Vimeo CDN to download sign clips not already cached — stated precisely as "core generative/semantic inference runs locally," not "fully offline." See `docs/SECURITY_AND_HYGIENE_AUDIT.md` for exact grep evidence.

**24. Scalability?**
Current prototype: sequential per-clip processing, in-memory job manager, single worker thread, no DB (job history read off disk, capped at 50 recent jobs), no auth. Clip download/trim is cached by catalog ID so repeated signs are never reprocessed. Production path (README §17, §15 Phase 3): GPU-served stronger local models, precomputed motion library, batch generation, parallel clip prep, model/version registry, audit logging, monitoring.

**25. What would you do with more time?**
Get qualified ASL-linguist review of gloss sequences and fingerspelling; build a curriculum-specific sign corpus beyond ZHO's general vocabulary; add pose-space transition blending instead of crossfades; strengthen the grounding heuristic beyond vocabulary overlap; add a real reviewer approval workflow/UI; run a formal end-to-end latency/throughput benchmark.

**26. What changes for production?**
Phase 1: real curriculum-approved source text, stronger grounding heuristic, cached/parallel clip prep. Phase 2: expert sign-language review, licensed sign corpus, non-manual grammar markers, pose-blended transitions, terminology governance. Phase 3: GPU-served models (re-benchmarked), precomputed motion cache, batch generation, model/version registry, audit logging, monitoring, evidence-justified avatar rig upgrade. (README §15, verbatim structure.)

**27. Why is this better than just prompting a cloud LLM directly for signs?**
A cloud LLM has no access to a verified sign-asset catalog and no mechanism to guarantee it only emits real, existing signs — it would either hallucinate glosses or require the same deterministic catalog-matching layer anyway, at which point the "AI generates signs directly" framing is misleading. This design puts a verifiable, inspectable, offline-capable deterministic layer between free-text LLM output and anything that gets rendered as a claimed sign — which is also what the brief's "must not introduce facts that cannot be traced back to source" and "local AI only" requirements demand structurally, not just as a compliance checkbox.
