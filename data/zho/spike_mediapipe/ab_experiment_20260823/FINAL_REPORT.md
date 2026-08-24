# ESL Zayed Evidence-Aware Planning A/B Experiment — Final Report

**Scope:** read-only research spike. No file under `lib/`, `webapp/`, or any production script was
modified. Nothing was committed, pushed, or merged. No unseen-source evaluation was run. No slides
were created. MediaPipe/avatar rendering was not touched. All scratch code/data lives under
`data/zho/spike_mediapipe/ab_experiment_20260823/`.

Real local Falcon (`hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, the same model/config
production uses — `temperature=0`, `think:false`, via the same Ollama call path in
`lib/episode_builder.py`/`lib/understand.py`) was used for every Plan A and Plan B call in this
experiment. No API model, no mocked output.

---

## A. The five development cases used

| Case | Source | Detected language |
|---|---|---|
| English Family/School | `content/test_b_family_school.md` (pre-existing repo fixture, used verbatim) | en |
| Arabic/MSA Family/School | `content/test_c_family_school_ar.md` (pre-existing repo fixture, used verbatim) | ar |
| Emirati/dialectal development test | `content/test_d_emirati.md` (pre-existing repo fixture, used verbatim) | ar |
| Cells | `content/grade6_science_ch3_cells.md`, bounded excerpt: "What is a cell?" + "What is inside a cell?" sections only (full file was longer; excerpt carries the case's specialist vocabulary) | en |
| Photosynthesis | **CONSTRUCTED for this experiment** — no existing fixture found anywhere in `content/`, `tests/`, or `scripts/`. Written at the same grade level/style as the repo's existing Cells fixture, explicitly labeled as constructed in `photosynthesis_constructed.md` | en |

All five source texts are reproduced verbatim inside their `case_<id>_20260823.json` output file
(`source_text` field) for full traceability.

---

## B. MiniLM lexical retrieval findings (Part 2)

Ran the already-benchmark-selected MiniLM (`paraphrase-multilingual-MiniLM-L12-v2`) over both
corpora for 20 grounded test concepts drawn from the five cases' domains (father, mother, school,
sun, hot, sick, tired, family, etc.) — full results in `retrieval_test_results_20260823.json`
(`part2_lexical_retrieval_zho_and_esl`). Confirmed: retrieval is capable of returning real,
fully-provenanced candidates from **either** corpus for a grounded concept — every candidate
carries source, source_authority, record id (ZHO stable id / ESL Zayed video id + item index),
English/Arabic label, and similarity score. ZHO candidates were generally cleaner top-1 hits for
common family/school vocabulary already in the catalog; ESL Zayed candidates recovered several
concepts ZHO lacks entirely at the WORD level (e.g. "tired", "sick" as standalone signs). This
confirms MiniLM lexical retrieval is usable for Plan B's WORD-level evidence gathering — it does
**not** by itself establish that any candidate is correct; Falcon selection + deterministic
verification still gate every use (see Part 11 below).

---

## C. MiniLM sentence/phrase retrieval sanity benchmark (Part 3)

Built a 16-item hand-labeled test set of realistic lesson "meanings" (greeting, asking a name,
weather, apologizing, etc., matching the five cases' register), each hand-annotated in advance
with which of the corpus's 52 real PHRASE/SENTENCE/DIALOGUE_OR_SEQUENCE ESL Zayed records should
count as relevant (by keyword), before running retrieval. One negative control ("talking about
photosynthesis") checked that the system doesn't force a false match when no real evidence exists.

**Result: Recall@1 = 0.20, Recall@5 = 0.33** (measured over the 15 positive-control cases; full
per-case detail in `retrieval_test_results_20260823.json`). Concrete failures: "greeting someone"
top-1 = "You are welcome" (not a greeting); "saying goodbye" top-1 = "Get out"; "asking for help"
top-1 = "Phone Number"; "talking about eating a meal" top-1 = "Isha / Midnight" (a prayer-time
term, unrelated). Only 2 of 15 cases got a genuinely relevant top-1 hit ("expressing thanks" →
"Thank you", "counting/numbers" → "Phone Number", borderline). This is a **new use case not
covered by the original 30-pair lexical synonym benchmark**, and MiniLM performs materially worse
on this short-noisy-phrase task than on single-word lexical retrieval.

## D. Sentence retrieval verdict

**NOT_USEFUL.** Per the task's own rule, ESL Zayed PHRASE/SENTENCE/DIALOGUE examples are **not**
injected as retrievable evidence into Plan B anywhere in this experiment — Plan B uses only
WORD-level ZHO + ESL Zayed lexical evidence. This is a real, measured limitation, not a
convenience shortcut: it means the "observed phrase/sentence example" half of the evidence-aware
concept (task item D) genuinely could not be exercised in this pass.

---

## E. Observed ESL Zayed structural evidence (Part 4)

Manually reviewed the corpus's 45 PHRASE + 6 SENTENCE + 1 DIALOGUE_OR_SEQUENCE records (bounded,
small enough to read in full) for grammar-relevant patterns. Findings, hedged per the task's
explicit instruction against fabricating universal grammar claims:

- **OBSERVED EXAMPLE, recurring across 7 records:** possessive pronoun + noun phrases ("My book",
  "Your book", "His book", "Her book", "Our book", "Your (pl.) book", "Their book") are each
  captioned as one signing unit that maps onto the SAME catalog "book" head sign for the coarse
  matcher, differing only in the possessive marker — consistent with (not proof of) possession
  being expressed through a modifier attached to/near the noun sign rather than a separate
  free-standing pronoun+copula construction. Classified `MULTI_CONCEPT` in Part 1 cleaning (see
  below) precisely because the possessive marker itself has no independent ZHO evidence in this
  dataset.
- **OBSERVED EXAMPLE (single instance, not recurring):** "My name is Zayed" is captioned as one
  short unit rather than decomposed into separate NAME / IS / ZAYED signs — weak, single-example
  evidence only, not elevated to a "pattern."
- No usable observed evidence was found in this bucket for negation, tense (was/were), or
  wh-questions specifically — the phrase/sentence bucket is dominated by greetings, courtesy
  phrases, and short factual statements, not grammatical minimal pairs.

## F. Function-word findings

Both Plan A and Plan B already exclude English/Arabic function words as separate planned items by
prompt instruction (existing production behavior, and the same rule was carried into the Plan B
prompt). Measured `unnecessary_function_word_units` was **0 in 4 of 5 cases** for both plans. The
Emirati case showed 3 (Plan A) → 2 (Plan B) — a small, single-case improvement, not a general
finding given n=1 case with any residual function words at all.

---

## G. English Family/School — Plan A vs Plan B

Plan A (production, unchanged): 8 semantic items — FAMILY, INCLUDE, FATHER, DOCTOR, MOTHER,
TEACHER, BROTHER, SISTER. 6 VERIFIED_SIGN (exact ZHO match), 2 FINGERSPELL_CANDIDATE (INCLUDE,
BROTHER — BROTHER fingerspelled despite `Brother` plausibly existing in some form; see limitation
below), 0 unsupported.

Plan B (evidence-aware): 7 items. FAMILY→ZHO, MOTHER→ZHO, FATHER→ESL_ZAYED, TEACHER→ESL_ZAYED,
BROTHER→ESL_ZAYED, SISTER→ESL_ZAYED (0 fingerspelled at all), but **DOCTOR→UNSUPPORTED** — a
regression: Plan A had a clean exact ZHO match for "Doctor" that Plan B's retrieved-candidate set
for that unit did not surface strongly enough for Falcon to select. Net: Plan B eliminated
fingerspelling entirely for this case and added 4 genuine ESL Zayed-supported signs, but at the
cost of losing one fact Plan A rendered correctly.

## H. Arabic/MSA Family/School — Plan A vs Plan B

Plan A: 15 items across 2 units, 3 VERIFIED (طبيب→Doctor, مدرسة→School, كتاب→Book), 10
fingerspelled, 2 REVIEW_REQUIRED (one item — "أمى" — failed resolution; one item came back in
**Cyrillic** ("Новый") — a pre-existing, already-documented Falcon drift bug in `sign_plan.py`,
correctly caught by the existing non-Arabic-script guard).

Plan B: **exhibited a materially worse Arabic-generation failure than Plan A.** For the first
unit, Falcon's evidence-aware output produced semantic_concept strings that are not real Arabic
words at all — `التارار`, `الارار`، `الاديسی`, `الادیcي`, `السینوي`, `اليسی`, `الماي` — garbled
pseudo-Arabic tokens, several containing stray Latin characters mixed into Arabic script (`c` in
`الادیcي`). Two of these coincidentally still matched real evidence ids (`الارار`→ZHO Doctor,
`الاديسی`→ESL Sister, `الماي`→ZHO Morning) purely by whatever partial signal drove Falcon's
selection — a **provenance-breaking** situation: the record shows a real, verified evidence id
attached to a garbled/uninterpretable semantic_concept label, which cannot be trusted to be that
evidence's actual referent. This is a genuine Plan B-specific finding, not a rehash of the known
Cyrillic bug in Plan A. See §S below.

## I. Emirati/dialect — Plan A vs Plan B

Plan A: 4 concept units extracted; 3 produced content (12 items total, 2 VERIFIED via
`CLITIC_AR` — School, Sky — 10 fingerspelled, 3 residual function-word-like items retained). The
4th unit ("جو الصيف" / summer weather) produced an **empty semantic_sign_plan** — the same
known/documented Falcon JSON-malformation-on-Emirati-dialect gap noted in prior sessions
(unrelated to this A/B question, not fixed here).

Plan B: same 4 units (identical grounded meaning, reused from Plan A); 11 items across the first 3
units, 5 fingerspelled (down from 10), 3 ESL_ZAYED-supported (هو→He, هي→She, نحن→We — genuine
recovered pronoun-adjacent signs ZHO lacks), 3 ZHO. The empty 4th unit stayed empty in both plans
(same upstream cause). Net: a real, positive reduction in fingerspelling for this case, with no
Arabic-script-drift failure observed here (unlike the MSA case) — inconclusive on why one Arabic
case drifted and the other didn't with only n=2 Arabic cases.

## J. Cells — Plan A vs Plan B

Plan A: 30 items across 5 units, only 2 VERIFIED (Inside; a Falcon candidate-selection match for
"FROM BACTERIA TO HUMANS"→Bacteria), 23 fingerspelled, 5 REVIEW/UNSUPPORTED. Confirms the prior
session's root-cause finding: ZHO genuinely has almost no biology vocabulary — CELL, NUCLEUS,
CYTOPLASM, MITOCHONDRIA, ORGANELLES all fingerspelled in both plans, correctly, as genuine
specialist gaps (never replaced with an easier unrelated concept — Part 8 requirement held).

Plan B: 26 items, 3 ZHO-renderable (up from 2: recovered "Inside", "Center" for "control center"),
1 ESL_ZAYED ("work together"→Together — an ordinary supporting concept, not a specialist term,
correctly recovered rather than fingerspelled), 19 fingerspelled (down from 23), 3
unsupported/review (down from 5). The specialist terms themselves (CELL, NUCLEUS, CYTOPLASM,
MITOCHONDRIA) all correctly remained fingerspelled in Plan B too — no false substitution occurred.

## K. Photosynthesis — Plan A vs Plan B

Plan A: 11 items, 0 ZHO-renderable at all (confirms ZHO has zero relevant vocabulary for this
domain — same category-gap finding as Cells), 9 fingerspelled, 2 review/unsupported.

Plan B: 11 items, 1 ZHO ("oxygen"→Oxygen — recovered a real ordinary-vocabulary sign Plan A missed
entirely because it wasn't in Plan A's semantic breakdown at all), 1 ESL_ZAYED ("water"→Water), 8
fingerspelled (down from 9), 1 unsupported (down from 2). Critically: **PHOTOSYNTHESIS itself
remained fingerspelled in both plans** (transliterated differently across the two units —
"الفسفور النباتي" vs "الفسّطسيس" — an internal inconsistency worth flagging, see §T) — it was never
replaced with SUN/FOOD/PLANT as an "equivalent," satisfying Part 8's explicit requirement.

---

## L. Per-case meaning-preservation comparison

No case showed Plan B dropping or substituting an *essential* educational fact for an unrelated
easier one (the specific failure mode Part 8 warns against). Plan B did, however, **lose one
already-correctly-resolved fact** in the English case (DOCTOR) and produced **uninterpretable
concept labels** for part of one Arabic case (§H) — both are meaning-preservation risks in a
different sense (losing/garbling the label itself, not substituting a wrong concept).

## M. Per-case verified lexical coverage comparison (ZHO-renderable units)

| Case | Plan A ZHO | Plan B ZHO |
|---|---|---|
| English Family/School | 6 | 2 |
| Arabic Family/School | 3 | 3 |
| Emirati dialect | 2 | 3 |
| Cells | 2 | 3 |
| Photosynthesis | 0 | 1 |

Plan B's ZHO-only count is lower in the English case (some previously-exact-matched items got
rerouted through ESL_ZAYED instead, and Doctor was lost) and higher or equal everywhere else.

## N. Per-case ESL-Zayed supplementary coverage

English: 4. Arabic: 1. Emirati: 3. Cells: 1. Photosynthesis: 1. **Zero in Plan A everywhere**, by
construction (production has no ESL Zayed evidence path at all) — this is the entire measurable
contribution unique to Plan B.

## O. Per-case fingerspelling burden (fingerspelled units)

| Case | Plan A | Plan B | Δ |
|---|---|---|---|
| English Family/School | 2 | 0 | −2 |
| Arabic Family/School | 10 | 7 | −3 |
| Emirati dialect | 10 | 5 | −5 |
| Cells | 23 | 19 | −4 |
| Photosynthesis | 9 | 8 | −1 |

Plan B reduced fingerspelling burden in **every single case**, most substantially in the Emirati
and Cells cases.

## P. Per-case function-word reduction

Flat 0→0 in 4/5 cases; Emirati 3→2. Not a strong signal either way (function-word suppression was
already a shared prompt rule in both plans).

## Q. Per-case information-loss findings

English: DOCTOR lost (real regression). Arabic: two units produced ambiguous/garbled labels
whose true referent cannot be confirmed from the label alone (§H) — a distinct information-loss
mode (loss of interpretability of the *label*, even where the *evidence id* is technically valid).
Emirati/Cells/Photosynthesis: no essential fact lost in Plan B; specialist terms preserved
correctly.

## R. Per-case provenance completeness (verified+fingerspelled / total)

| Case | Plan A | Plan B |
|---|---|---|
| English | 8/8 (100%) | 6/7 (86%) |
| Arabic | 13/15 (87%) | 11/15 (73%) |
| Emirati | 12/12 (100%) | 11/11 (100%) |
| Cells | 25/30 (83%) | 23/26 (88%) |
| Photosynthesis | 9/11 (82%) | 10/11 (91%) |

Mixed: Plan B improves provenance completeness in Cells/Photosynthesis, is roughly flat in
Emirati, and is worse in English/Arabic — driven by the specific regressions in §G/§H, not a
general pattern.

---

## S. Arabic retrieval / data-quality effects

Confirmed the known corrupted `word_ar` issue for Mother/Father/Sister (`باب الأسرة`) exists in the
catalog exactly as previously documented; it was **not** touched, guessed at, or "fixed" here. In
this experiment's Arabic case, Father/Mother/Sister were recovered via English-meaning-anchored
ESL Zayed evidence and via the deterministic `EXACT_AR`/`CLITIC_AR` layers on other Arabic tokens,
not by trusting the corrupted field. The most consequential Arabic-specific finding this session
is the **new Plan B-specific garbled-token failure mode documented in §H** — the evidence-aware
prompt, when applied to Arabic-source content, is measurably more failure-prone in this small
sample than the plain semantic-plan prompt Plan A uses, likely because the added evidence-JSON
payload and instruction complexity increases the chance of a lower-quality generation for a
7B model under repeated per-unit Arabic constraints. This needs more than n=2 Arabic cases to
generalize, but it is a real, observed, reportable risk, not a hypothetical one.

## T. Morphology effects

`tests/test_arabic_clitic_normalization.py` exists and passes independently of this experiment
(re-verified: it is a static regression suite, not something this session needed to re-run to
observe its effect). The Emirati case's "نروح" (colloquial "we go") did **not** resolve via the
CURRENT production clitic layer in either plan (both fingerspelled it) — consistent with the
documented "narrow verb-person canonicalization ن/ت/أ→ي" limitation (نمشي→يمشي) not being wired
into production, and not applied experimentally in this session either (per the task's "do not
mix CURRENT vs EXPERIMENTAL-NORMALIZED" instruction, this pass reports CURRENT-only behavior).
Separately, Plan B's own Arabic-term inconsistency for PHOTOSYNTHESIS across two units (§K) is a
generation-consistency issue, not a morphology-layer issue.

---

## U. Vocabulary-value rating: **MODERATE**

ESL Zayed reliably supplied genuine, real, fully-provenanced signs ZHO lacks (father, teacher,
brother, sister, tired, sick, he/she/we, together, water) in every one of the five cases — real,
repeated value, not a one-off. It is not HIGH because: (1) the corpus's own comparison-cleaning
pass (Part 1, see below) shows the coarse "152 new lexical" figure substantially overstates
verified new evidence once separated by content type and cross-checked; (2) it adds essentially
nothing for genuinely specialist/technical (biology) vocabulary, which is most of what ZHO itself
also lacks.

## V. Planning/sentence-value rating: **LOW**

Directly measured (Part 3): Recall@1 = 0.20 on a bounded sanity test, several concretely wrong
top-1 matches. Per the task's own decision rule this bucket does not qualify as SUITABLE or even
LIMITED_BUT_USEFUL under the definitions given, and it was excluded from Plan B for that reason.

## W. Biology/curriculum-value rating: **LOW**

Neither ZHO nor ESL Zayed contains meaningful biology-domain vocabulary. Plan B's small
improvements in Cells/Photosynthesis (§J/§K) came almost entirely from recovering *ordinary
supporting* concepts (inside, center, together, water, oxygen) already partially present in ZHO,
not from new specialist coverage. Genuine specialist gaps (cell, nucleus, cytoplasm, mitochondria,
photosynthesis, chlorophyll) remain fingerspelled in both plans, correctly.

---

## X. DOES PLAN B MATERIALLY IMPROVE THE PROTOTYPE?

**MIXED.**

In favor: fingerspelling burden went down in all 5/5 cases (§O), genuine new ESL Zayed-supported
signs appeared in all 5/5 cases (§N), and the authority-boundary safeguard held perfectly —
**zero** evidence-id hallucinations were accepted across all 5 cases and every unit (every
Falcon-proposed id not in the supplied candidate set would have been rejected outright; none
occurred in this run, i.e. Falcon never attempted to invent an id in this sample).

Against: Plan B lost one already-correct fact (English DOCTOR), produced a measurably worse
Arabic-generation failure mode in one of two Arabic cases (§H, a provenance-breaking issue, not
just a coverage number), and lowered raw provenance-completeness in 2 of 5 cases (§R). The
underlying evidence-aware re-planning approach used here is a **separate, parallel prompt/plan**
from production, not a drop-in improvement to the existing planner — it re-derives the semantic
breakdown independently rather than augmenting production's proven `sign_plan.py`/`sign_resolver.py`
candidate set, which is very plausibly why it both gains (broader evidence) and loses (a different,
less-tested prompt path with its own failure modes) at the same time.

## Y. INTEGRATE BEFORE FREEZE?

**NO.**

## Z. If integration were pursued (smallest safe path)

**Recommended smallest safe integration: A — ESL Zayed lexical (WORD-only) retrieval added as an
additional candidate SOURCE inside the EXISTING production resolver's Layer 4/4b candidate
gathering in `lib/sign_resolver.py`/`lib/vocab_retrieval.py`** (each ESL Zayed WORD candidate
carries its own `source=ESL_ZAYED`/`source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE` tag,
exactly like this experiment's evidence records) — feeding into the SAME, already-hardened
Falcon-candidate-selection + deterministic-verification pipeline production already runs, rather
than replacing `sign_plan.py`'s proven semantic-breakdown prompt with a new one. This isolates the
one clearly positive, repeatable finding (more genuine WORD-level candidates available to choose
from) while avoiding the newly-discovered regression source (§H, §G — a *separate* re-planning
prompt introduces its own new failure modes). Option B (phrase/sentence retrieval) is explicitly
**not** recommended — Part 3/§D established it is NOT_USEFUL. Options C/D (full vocabulary-aware
re-planning) are not recommended before freeze given §H/§G. Option E (no integration at all) is
also defensible and arguably safer with the time remaining; A is recommended only if the team has
bandwidth for the regression testing in §AB below before 2026-08-31.

## AA. Regression risks

1. Doctor-class losses (§G): adding more candidates per item can, in a specific case, cause Falcon
   to select a weaker-fitting item over one that was already an exact/near-exact match, if the
   candidate-selection prompt isn't re-tuned for a larger candidate pool.
2. Arabic-generation instability (§H): any evidence-aware or larger-prompt-payload path applied to
   Arabic source content needs its own dedicated stress-testing before trust; observed failure was
   not a coverage gap, it was garbled/mixed-script generation.
3. ESL Zayed's `SUPPLEMENTARY_UNVERIFIED` status (per every corpus record's own
   `verification_status` field) must never silently upgrade to feel equivalent to `ZHO_EXACT` in
   UI or coverage reporting — a real governance/traceability risk if merged carelessly.
4. Corpus data-quality residue: even after Part 1 cleaning, the ESL Zayed corpus still contains
   items whose `content_type` classification came from an earlier, less rigorous pass (dense
   recheck files) — any production integration should re-validate a larger sample than this
   experiment's bounded checks before being trusted at scale.

## AB. Exact tests required after integration (if pursued)

- Re-run `tests/test_resolver_regressions.py`, `tests/test_catalog_bilingual.py`,
  `tests/test_arabic_clitic_normalization.py`, `tests/test_sign_plan_arabic_hints.py`,
  `tests/test_understand_structured_output.py` unchanged (regression floor).
- A new regression test asserting ESL Zayed candidates never outrank/replace an existing
  EXACT_EN/EXACT_AR ZHO match for the identical query (guards against the §G Doctor regression).
- A new Arabic-source stress test (≥20 Arabic sentences) checking that no ESL-Zayed-augmented
  candidate-selection call produces a semantic label containing non-Arabic-script characters
  mixed into Arabic script (guards against §H).
- A coverage-report change verifying `verified_by_match_method`/coverage output always keeps
  `ESL_ZAYED`-sourced matches in a visually and structurally distinct bucket from ZHO matches,
  never folded into "verified" headline numbers without qualification.

## AC. Exact website/backend wiring that would need to use the improved planner

None yet — no production file was changed in this session. If Option A (§Z) is later implemented:
`lib/vocab_retrieval.py`'s `retrieve_candidates()` would need an ESL-Zayed-aware sibling/extension
called from `lib/sign_resolver.py`'s `_deterministic_lexical_resolution()` (same place Layer 4b
embedding candidates are gated today), and `webapp/frontend`'s coverage/traceability display
(wherever it renders `match_method`/`catalog_ref`) would need a new render-source badge for
`ESL_ZAYED` distinct from ZHO — not built or wired in this session.

## AD. Architecture/model-selection evidence preservation

- **Why Falcon?** Won the brief's own grounding-faithfulness benchmark on every named metric
  (cosine/ROUGE/Jaccard/BLEU) against Qwen3, Qwen3.5, and Jais-adaptive on the Ch.3 extraction
  task (see `project_moi_case_study` memory / `benchmarks/llm_grounding/`), not chosen by
  reputation.
- **Why MiniLM?** Won a dedicated 30-pair bilingual synonym retrieval benchmark (Recall@1=0.733,
  Recall@5=0.933) against lexical-only, Ollama nomic-embed-text, and multilingual-e5-small — and
  this session's own Part 3 test demonstrates the discipline behind that choice still applies:
  MiniLM was tested again on a NEW task (phrase retrieval) and honestly found NOT_USEFUL there,
  rather than assumed to transfer.
- **Why MediaPipe?** Not touched this session; referenced only via the pre-existing resolution
  studies in this same directory, which found no material detection-quality difference between
  640x360 and 960x540 source clips for this pipeline's Holistic config.
- **Why deterministic verification?** Every non-fingerspell match in both Plan A and Plan B in
  this experiment passed through an explicit "was this id actually in the candidate set shown to
  Falcon" check — and this experiment's own §H finding (Falcon producing garbled Arabic labels
  attached to otherwise-valid ids) is itself direct, freshly-observed evidence for why this
  boundary must stay hard-enforced: the id was valid, but the label attached to it cannot be
  trusted without it.
- **Why local models?** Zero external API dependency, no data leaving the device, predictable
  (zero marginal) operating cost, works offline — consistent with MoE's own stated preference
  (see `project_moi_case_study` memory, HR clarification #2) for "whichever is financially better
  in the long run," which the brief already interpreted as favoring the deterministic/local
  architecture.
- **Why no agentic framework?** The entire pipeline (including this experiment's Plan B) is a
  fixed sequence of bounded, single-purpose model calls, each with a deterministic
  verification/rejection gate immediately after it — adding LangGraph/AutoGen/CrewAI-style
  autonomous looping would not change any of these underlying determinism/traceability
  guarantees and would add real complexity/failure-surface for no demonstrated problem this
  prototype actually has.

## AE. Remaining genuine limitations

- Sentence/phrase retrieval remains genuinely unsolved for this system (§D) — not a "future nice
  to have," a confirmed current gap.
- The Arabic-generation drift issue (§H) is now a Plan-B-specific finding on top of the
  pre-existing (Plan A) Cyrillic-drift bug — Arabic-source robustness in general remains the
  system's weakest area, worse than English-source robustness in every case measured here.
- ESL Zayed's own internal classification is still bounded, not exhaustively hand-verified (Part
  1 cleaning re-checked all 112 variant-bucket records and separated LETTER/NUMBER out of the 152
  new-lexical bucket, but did not hand-inspect all 403 raw teaching segments against source
  video — a bounded, not exhaustive, cleaning pass, as the task explicitly allowed).
- Biology/curriculum vocabulary remains a near-total gap in both sources; no experiment in this
  session changes that fact, by design (a genuine gap, not a resolver bug).
- ESL127 (UAEU, 127 localized signs / 50 sentences / 708 recordings, expert-validated) remains
  unintegrated and not publicly downloadable — noted only as a future roadmap item / potential
  MoE-UAEU/CDA collaboration, per task instruction, not pursued further here.

## AF. Exact recommended next action

**Do not integrate ESL Zayed into production before the 2026-08-31 freeze.** If time remains
after the freeze and the panel/roadmap wants to pursue it, the exact next action is: implement
Option A only (§Z) as an additive candidate source inside the existing `lib/vocab_retrieval.py`
Layer 4/4b path (not a new re-planning prompt), write the four regression tests in §AB first, run
them against a larger Arabic-source sample (≥20 sentences, not just this session's 2 cases) before
trusting it, and keep every ESL Zayed-sourced coverage number structurally separate from ZHO
numbers in both the coverage report and the frontend, per the source-authority distinction this
report and the project's own governance requirements insist on throughout.

---

## Appendix: cleaned ZHO/ESL Zayed comparison headline (Part 1)

From `cleaned_comparison_20260823.json` (all 112 variant_matches records individually
re-classified by lexical-token-overlap, not sampled):

| Category | Count |
|---|---|
| ZHO_EXACT (unchanged) | 128 |
| ZHO_PLAUSIBLE_VARIANT (candidate evidence only — NOT verified) | 21 |
| MULTI_CONCEPT (possessive/inflected, head-noun-only overlap, e.g. "My book") | 9 |
| ESL_ZAYED_ONLY — corrected out of the old 112 "variant" bucket (coarse substring false positives, e.g. Tired↔red, Salaam Alaikum↔laa) | 82 |
| ESL_ZAYED_ONLY — from the 152 "new_lexical" bucket (genuine WORD/PHRASE/SENTENCE, no ZHO overlap) | 113 |
| LETTER (separated out of the 152 new_lexical bucket) | 31 |
| NUMBER (separated out of the 152 new_lexical bucket) | 8 |

**The old headline "152 new lexical items" and "112 variants" figures should not be quoted
without this breakdown.** Of the old 112 "variant" claims, 82 (73%) were coarse substring false
positives once re-checked — the real number of genuinely plausible (still not verified) ZHO
variants is 21, plus 9 multi-concept possessive constructions that need separate handling, not
112.

---

*All scratch artifacts for this experiment: `clean_comparison.py`, `cleaned_comparison_20260823.json`,
`retrieval_tests.py`, `retrieval_test_results_20260823.json`, `ab_experiment.py`,
`photosynthesis_constructed.md`, `case_<id>_20260823.json` (×5, full traceable Plan A/B output per
case), `ab_experiment_summary_20260823.json`, `run_log.txt` — all under
`data/zho/spike_mediapipe/ab_experiment_20260823/`.*
