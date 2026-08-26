# Presentation Evidence Gaps — Reference for Slide Writers

Evidence-recovery pass only. No production code, slides, or experiments were touched. Every
claim below is backed by an exact repo-relative path; anything without independent artifact
support is marked NOT VERIFIED.

---

## 1. Alyah / Emirati-dialect benchmark

**VERIFIED CLAIM**

- Exact claim: TII's public "Alyah" Emirati-dialect benchmark (1,173 MCQs across 7 categories)
  was run against 4 locally-hosted candidate models; Falcon-H1-7B-Instruct scored highest at
  64.88% accuracy (100% parse rate).
- Evidence: real checkpoint/result files, not just narrative. `alyah_test.parquet` is the actual
  HuggingFace dataset (`tiiuae/alyah-emirati-benchmark`), `alyah_checkpoint.jsonl` is the raw
  per-question-per-model log, `alyah_eval_FINAL.log` is the scored JSON summary. Per-model
  breakdown confirmed in the log: Falcon-H1-7B 761/1173 correct (64.88%); Qwen3-8B 752/1173
  (64.11%); jais-adaptive-7B 603/1173 (51.41%, 99.49% parse); Qwen3.5-9B 305/1173 (26.00%).
- Repo path: `benchmarks/alyah/run_alyah_eval.py` (eval script), `benchmarks/alyah/alyah_test.parquet`
  (dataset), `benchmarks/alyah/results/alyah_checkpoint.jsonl` (raw),
  `benchmarks/alyah/results/alyah_eval_FINAL.log` (final scored output), `benchmarks/README.md`
  (methodology narrative).
- Metric: 1,173 questions, Falcon-H1-7B-Instruct-GGUF:Q4_K_M = 64.88% accuracy, 100% parse rate.
  IMPORTANT — this is a **secondary/supplementary** benchmark, not the primary model-selection
  benchmark. The primary, brief-mandated benchmark is the separate Ch.3 grounding-faithfulness
  eval (`benchmarks/llm_grounding/`, also Falcon-H1 winner: cosine 0.908/ROUGE-1 0.755/ROUGE-L
  0.734/Jaccard 0.664/BLEU 0.597). Do not present Alyah as if it were the model-selection
  criterion.
- Safe wording for slide: "On a supplementary 1,173-question Emirati-dialect benchmark (TII's
  public Alyah dataset), our selected model (Falcon-H1-7B) scored 64.88% — the best of 4 models
  tested locally, essentially tied with Qwen3-8B (64.11%)."
- Deeper panel-defense wording: "This is context, not the selection criterion — model selection
  was made on the brief's own grounding-faithfulness benchmark (Ch.3 extraction task), where
  Falcon-H1 also won on every named metric. Alyah is honest supporting evidence: it also shows a
  publicly-reported closed Arabic-specialist model (falcon-h1-arabic-7b-instruct, not deployable
  locally) scores 82.18% on the same benchmark — we're citing the gap, not hiding it, as the
  argument for a future MoE↔TII partnership or fine-tuning path (see `README.md` lines ~42-46 for
  the exact framing)."

**Separately — NOT VERIFIED / DO NOT USE:** README.md explicitly documents that a
"developer-reported ~83% figure for a larger/different Falcon configuration on a related
vocabulary/language evaluation" was checked against this repo and found **not backed by any
script or result file here**. This is explicitly flagged in-repo as DEVELOPER-REPORTED / NOT YET
VERIFIED (`README.md:44`). Do not conflate this with the real, artifact-backed 64.88% Alyah number
above, and do not present the ~83%/82.18% figures as this project's own measured result — 82.18%
is TII's own published leaderboard number for a different, non-deployable model, cited for
context only.

---

## 2. Temporal BEFORE → spatial أمام regression ("Blocker A")

**VERIFIED CLAIM**

- Exact claim: English "before" used temporally (e.g. "before school starts") was, before the
  fix, silently auto-verified as the catalog's spatial "in front of" sign (أمام) via an
  unguarded exact bilingual string match — a real semantic-substitution bug, not hypothetical.
- Root cause (two-layered, per commit `ac59c07`):
  1. The catalog's "Directions and Locations" category row `word_en="Before"` (spatial
     preposition, `item_url=.../Before_4728`) was trusted by Layer 1 exact-match as
     `LOSS_FULL`/auto-verified with no polysemy check.
  2. Even after gating Layer 1, `lib/vocab_retrieval.py`'s `morphology_match()` whole-phrase
     branch had no `form != word` guard, so the identity form silently let the same string back
     in through Layer 2, bypassing the new gate.
- Fix (commit `ac59c07`, "Fix Blocker A: temporal BEFORE no longer silently authorized as spatial
  أمام"): introduced `AMBIGUOUS_POLYSEMY_CATEGORIES_EN = {"Directions and Locations"}` in
  `lib/sign_resolver.py` — a category-level rule (covers every row in that category, e.g. Before,
  After, Over) that routes any exact match against a flagged row through the same Falcon
  contextual-confirmation + information-loss gate as a retrieval candidate, instead of
  auto-accepting. Also fixed the missing identity-form guard in
  `lib/vocab_retrieval.py`'s `morphology_match()`.
- Follow-up fix (commit `f96d35b`, "Fix live-observed Blocker A recurrence: force explicit
  sense-disambiguation for ambiguous-category candidates"): live-observed during a real
  (non-mocked) Falcon HTTP run that the category gate correctly routed the candidate through
  confirmation, but Falcon sometimes rubber-stamped it anyway ("The candidate 'Before' matches
  the semantic item 'BEFORE' in context" — no actual temporal-vs-spatial reasoning). Fixed by
  attaching an explicit `ambiguity_warning` field to any candidate in a flagged category, and
  updating `CANDIDATE_SELECTION_SYSTEM_PROMPT` to require Falcon to state IN THE REASON why the
  shown sense specifically applies, answering NONE otherwise.
- Catalog row: `data/zho/catalog.json:5244` — `"word_en": "Before"` (spatial, category
  "Directions and Locations", word_ar = "أمام").
- Regression tests (`tests/test_resolver_regressions.py`):
  `test_temporal_before_not_silently_authorized_as_spatial_amam`,
  `test_temporal_before_rejected_when_falcon_says_none_in_context`,
  `test_spatial_before_still_resolvable_via_falcon_confirmation` (over-correction guard — a
  genuinely spatial "before" still resolves correctly), plus
  `test_ambiguous_category_candidate_carries_explicit_sense_disambiguation_warning` (added in
  `f96d35b`).
- Real E2E job evidence: commit `f96d35b`'s message states the exact wording "eat breakfast
  before school starts" was verified live, repeatedly, against real (non-mocked) Falcon — 3/3
  correct rejections of أمام after the fix, falling through to safe fingerspelling; a genuinely
  spatial use ("stand before the class") still resolved to the spatial sign. Commit `5b68fe4`
  ("Add E2E regression fixtures for Blockers A/B and ESL Zayed materialization") added
  `content/e2e_regression/fixture_h_temporal_before.md` and references real job IDs
  `03e42695af09`, `78a10ec88975`, `42738ec3b817` run against a live uvicorn instance of
  `webapp/backend` — the job IDs themselves are cited in the commit message, not reproduced as a
  standalone log file in this pass (raw HTTP job logs were not located as separate artifacts;
  treat the job-ID citation as commit-message-level evidence, not a separately verifiable log
  file).
- Final safe behavior: exact-string matches against polysemous spatial/directional catalog
  categories are never auto-verified; they must pass explicit LLM sense-disambiguation with a
  named ambiguity warning, and default to safe fingerspelling (not silent wrong-sign selection)
  when the sense doesn't match.
- Safe wording for slide: "We found and fixed a real semantic bug: the English word 'before' used
  in a time sense ('before school starts') was being silently matched to the sign for spatial
  'in front of.' The fix requires explicit sense-checking before any spatial/directional sign is
  used, with automatic fallback to safe fingerspelling when uncertain — verified live against the
  real model, 3/3."
- Deeper panel-defense wording: "This was caught in two passes — a deterministic category-level
  gate fixed the structural bug, then a live quantified-experiment run (§16 in project records)
  caught that the LLM confirmation step itself didn't always reason about the ambiguity even when
  correctly routed through the gate, so we hardened the prompt to force explicit justification.
  This is an honest example of 'gate the LLM, then verify the gate actually works under real
  model behavior' — not a one-shot fix. Full diff: commits `ac59c07`, `f96d35b`;
  `lib/sign_resolver.py`, `lib/vocab_retrieval.py`."

---

## 3. "SCHOOL STARTS" → "SCHOOL" information-loss regression ("Blocker B")

**VERIFIED CLAIM**

- Exact claim: the sentence "School starts early." was, before the fix, capable of collapsing to
  a single semantic-plan item `["SCHOOL"]` — silently dropping the predicate START — and being
  reported as a clean "OK" plan with no trace of the loss.
- Root cause (commit `7ca3ffa`, "Fix Blocker B: SCHOOL STARTS no longer silently drops the START
  predicate"): `build_sign_plan()` in `lib/sign_plan.py` accepted whatever JSON array the local
  model (Falcon) returned with no check that a single-item plan for a multi-concept sentence was
  legitimate.
- Fix: added a conservative deterministic guard — when the sentence's own distinct content-word
  count (via existing `_tokenize_en`/`_tokenize_ar`, stopwords stripped) is ≥2 but the plan
  collapsed to exactly one item, the unit is flagged `semantic_plan_status = "REVIEW_REQUIRED"`
  and `possible_information_loss = True` instead of `"OK"`. The already-produced item(s) are kept
  (never silently discarded); `resolve_unit()` in `lib/sign_resolver.py` propagates this as
  `review_required = True` so the collapse can never silently vanish downstream.
- Guard location: `lib/sign_plan.py` (see diff in commit `7ca3ffa`); propagation guard in
  `lib/sign_resolver.py`'s `resolve_unit()` (also touched again in `ac59c07`'s diff, which
  additionally OR's in `unit.get("possible_information_loss")` and
  `unit.get("semantic_plan_status") == "REVIEW_REQUIRED"`).
- Regression tests (`tests/test_resolver_regressions.py`):
  `test_school_starts_single_item_collapse_flagged_not_silent` (mocks the model to return
  `'["SCHOOL"]'`, asserts `semantic_plan_status == "REVIEW_REQUIRED"`,
  `possible_information_loss is True`, and that `resolve_unit()` propagates `review_required is
  True`), `test_school_starts_two_item_plan_not_flagged` (over-correction guard — a legitimate
  `["SCHOOL", "START"]` plan is NOT flagged).
- Real E2E job evidence: commit `5b68fe4` added `content/e2e_regression/fixture_i_school_starts.md`
  as one of the three fixtures proven through the real FastAPI HTTP path (same job-ID citations as
  Blocker A above — `03e42695af09`, `78a10ec88975`, `42738ec3b817` — cited in the commit message,
  not as a separately reproduced log file).
- Final safe behavior: any single-item semantic collapse of a sentence with ≥2 distinct content
  words is flagged for review rather than silently accepted as complete; nothing is silently
  deleted.
- Safe wording for slide: "We added a deterministic safety check that catches when the AI's
  sentence breakdown accidentally drops a word's meaning (e.g. 'school starts' losing 'starts') —
  flagged for review automatically, never silently lost."
- Deeper panel-defense wording: "This is a conservative content-word-count heuristic, not a
  parser — it can't prove a single-item plan is wrong, only that it's suspicious enough (≥2
  distinct content words collapsing to 1 item) to require review rather than silent
  auto-acceptance. Two regression tests lock in both the failure catch and the
  no-over-correction case. `lib/sign_plan.py`, commit `7ca3ffa`."

---

## 4. ESL Zayed enrichment / scaling story

**VERIFIED CLAIM (with explicit confidence-tier separation from ZHO)**

**Preserve this distinction on every slide:** ZHO (`data/zho/catalog.json`, 1,143 entries) is the
institutional, verified primary catalog (UAE Zayed Higher Organization government dictionary).
ESL Zayed is supplementary, **`verification_status: "SUPPLEMENTARY_UNVERIFIED"`** on every single
record (confirmed in `data/zho/esl_zayed_supplementary_catalog.json`), sourced from YouTube
educational videos, not a government-verified dictionary. Never present ESL Zayed numbers as
equivalent confidence to ZHO numbers.

- **Total accessible channel videos:** 93 (`data/zho/spike_mediapipe/esl_zayed_full_93video_corpus_20260823.json`,
  a 403-record JSON list of teaching segments across 93 videos; also stated directly in
  `data/zho/spike_mediapipe/esl_zayed_caption_pilot_20260823/PILOT_FINDINGS.md`).
- **Total teaching segments across corpus:** 403 (confirmed by direct count of
  `esl_zayed_full_93video_corpus_20260823.json`, and cited in `PILOT_FINDINGS.md`: "403 records /
  93 non-alphabet-heavy [videos] but including two ~30-item letter videos").
- **Failed naive pixel-diff/caption-difference segmentation pilot:** commit `15be2f4` ("Pilot ESL
  Zayed caption-state segmentation on 8 real videos — do not scale"); full writeup in
  `data/zho/spike_mediapipe/esl_zayed_caption_pilot_20260823/PILOT_FINDINGS.md`. Frame-differencing
  on 8 hand-picked pilot videos: **0/8 AUTO_ACCEPT**, 2/8 REVIEW_REQUIRED (with documented boundary
  doubts even on those two), 6/8 REJECT_SEGMENTATION (gross count errors, e.g. one 28s video
  detected as a single segment when 8 items were expected, one video over-segmented 26→57).
  Explicit "DO NOT SCALE (OUTCOME B)" verdict in the pilot doc. Root causes documented: no single
  fixed caption region works across ≥3 distinct on-screen templates in the corpus; hand motion
  inside/near the caption region contaminates the diff signal; a single global threshold doesn't
  generalize across region sizes.
- **Successful OCR caption-identity alignment method:** replaced frame-differencing with sparse
  OCR run only near suspected transitions, matched against the already-known ordered
  Arabic/English label sequence for that video (a constrained alignment problem, not open-ended
  change detection). First proven in commit `8cb3ccd` ("OCR caption-identity segmentation: expand
  safe WORD catalog 20 → 66"), explicitly framed as "replaces v1's failed pixel-diff approach."
- **Template clustering / scaling results:** commit `ce4fda2` ("Template-clustering scale-up:
  fingerprint/cluster 35 videos, OCR-align 31, catalog 66→122") — deterministic per-video
  block-variance layout fingerprinting + union-find clustering on cosine similarity found one
  dominant "right_box" template (30/37 videos in that batch) plus a smaller TEMPLATE_2 and 5
  singletons; confirmed in the final `cluster_summary.json`
  (`data/zho/spike_mediapipe/esl_zayed_template_scale_20260824/cluster_summary.json`):
  `n_videos: 93`, `TEMPLATE_1` cluster has 84 videos, `TEMPLATE_2` has 4, plus 5 singletons.
  Manual verification caught real fingerprinting errors (documented false-merges of NUMBER/LETTER
  videos into TEMPLATE_1 by background/signer similarity, correctly rejected at the OCR
  quality-gate stage rather than silently force-matched).
- **Safe production WORD catalog growth milestones (chronological, each backed by a distinct
  commit and rebuilt catalog file):**
  1. 20 words — pre-existing baseline before any scaling pass (referenced as starting point in
     `8cb3ccd`, `PILOT_FINDINGS.md`).
  2. 20 → 66 — commit `8cb3ccd`, 12 videos processed (3 pilots + 9 additional), 22/22 regression
     tests pass.
  3. 66 → 122 — commit `ce4fda2`, 22 AUTO_ACCEPT / 4 REVIEW_REQUIRED / 5 REJECT out of 31
     OCR-aligned videos; regression suites re-verified (14/14, 8/8, 5/5 across three test files).
  4. 122 → 244 (final) — commit `79e8b7b`, 86 further videos gated: 65 AUTO_ACCEPT (76%), 16
     REVIEW_REQUIRED, 5 REJECT. Rebuilt catalog deduped on (video, normalized-Arabic-text); spot
     check found 0 duplicate pairs, 0 missing English/Arabic fields, 100% `content_type=WORD`.
     Regression suite: 27/27 pass.
  - **Final safe production WORD count: 244 records**, independently confirmed by direct read of
    `data/zho/esl_zayed_supplementary_catalog.json` (`len() == 244`).
- **Quality gate discipline:** every scale-up pass used the same
  AUTO_ACCEPT / REVIEW_REQUIRED / REJECT rule (`quality_gate.py`, full count + monotonic +
  non-overlapping + no-duplicate-intervals only → AUTO_ACCEPT), never a blanket accept.
- **Source video ID / timestamp preservation:** every catalog record carries
  `youtube_video_id`, `source_url`, `segment_start_s`, `segment_end_s` — confirmed by direct
  inspection of a real record in `data/zho/esl_zayed_supplementary_catalog.json`
  (`ESL_ZAYED_0001`: `youtube_video_id: "DJqUtzA2OgE"`, `segment_start_s: 6.0`,
  `segment_end_s: 7.0`).
- **Why only WORD-level content entered production (not sentences/phrases):**
  `data/zho/spike_mediapipe/esl_zayed_template_scale_20260824/exact_phrase_match_investigation.md`
  — investigated whether exact/normalized-text phrase matching (a fundamentally different,
  zero-fuzzy-tolerance approach vs. the rejected embedding-similarity method) could safely admit
  PHRASE/SENTENCE evidence. Found it architecturally sound in principle but empirically useless:
  a case-folded substring test of all 47 non-empty English PHRASE/SENTENCE strings against the
  full text of all 5 dev fixtures produced **zero exact matches** — real LLM-generated lesson
  phrasing essentially never reproduces a fixed canned classroom phrase verbatim. Not wired into
  `lib/sign_resolver.py`; explicitly reported as a finding only.
- **Sentence/phrase retrieval rejection evidence (separate, earlier finding):**
  `data/zho/spike_mediapipe/ab_experiment_20260823/FINAL_REPORT.md` §C/§D — a 16-item hand-labeled
  MiniLM sentence-retrieval sanity benchmark measured **Recall@1 = 0.20, Recall@5 = 0.33** over 15
  positive-control cases, with concrete wrong top-1 matches documented (e.g. "greeting someone" →
  "You are welcome"; "saying goodbye" → "Get out"). Verdict: **NOT_USEFUL**, and PHRASE/SENTENCE
  examples were never injected into the evidence-aware planning experiment as a result.
  `run_alyah_eval.py`-style provenance discipline is echoed here — every claim in that report is
  tied to `retrieval_test_results_20260823.json`.
- Regression tests covering ESL Zayed integration guardrails: `tests/test_esl_zayed_supplementary.py`
  — 16 tests including `test_doctor_resolves_via_zho_exact_not_esl_zayed`,
  `test_esl_zayed_never_consulted_when_zho_exact_succeeds` (ZHO-priority guard),
  `test_esl_zayed_candidate_rejected_if_not_in_candidate_set`,
  `test_coverage_report_keeps_zho_and_esl_zayed_separate` (confirms the confidence-tier
  separation is enforced in code, not just policy).
- Safe wording for slide: "We identified 93 accessible educational sign-language videos on
  YouTube (403 teaching segments). After a naive automatic-segmentation approach failed
  completely (0/8 videos correctly split in a pilot test), we built a more careful OCR-based
  identity-matching method and scaled it across the corpus with a strict accept/review/reject
  gate — growing a supplementary vocabulary catalog from 20 to 244 words, each one traceable back
  to its exact source video and timestamp. This supplementary catalog is clearly separated from
  our verified government-dictionary catalog everywhere in the system."
- Deeper panel-defense wording: "Every stage of this scale-up is falsifiable and logged: the
  pixel-diff approach's failure is documented with per-video error counts, not glossed over; the
  OCR method's yield rate (65-76% AUTO_ACCEPT per batch) is consistent across batches, which is
  itself evidence the method generalizes rather than being tuned to one lucky sample; and we
  explicitly tested and rejected two ways of getting sentence-level value out of this corpus
  (embedding retrieval: Recall@1=0.20; exact-phrase matching: 0/47 real matches) rather than
  quietly not trying. Every record's `verification_status` field is literally the string
  `SUPPLEMENTARY_UNVERIFIED` — we do not claim these are validated Emirati Sign Language, only
  observed candidates gated by a resolver that always prefers the verified ZHO catalog first
  (`test_esl_zayed_never_consulted_when_zho_exact_succeeds`)."

---

## Cross-cutting notes for slide writers

- Every number above traces to a file that exists in the repo right now; none were reconstructed
  from memory. Where a claim (e.g. specific HTTP job IDs) is only available as text inside a
  commit message rather than as a separately reproducible log file, that limitation is called out
  explicitly above — treat it as weaker evidence than a standalone artifact and hedge accordingly
  if pressed on it live.
- The one explicit NOT VERIFIED item (the ~83%/82.18% "larger Falcon" figure) is already
  correctly caveated in `README.md` itself — the repo is honest about this on its own; slides
  should preserve that honesty rather than smoothing it over.
