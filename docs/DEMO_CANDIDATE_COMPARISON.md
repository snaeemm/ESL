# Demo Candidate Comparison (Release Audit)

Survey basis: sampled 20+ job directories across `outputs/webapp_jobs/` (114 total) and
`outputs/*` named runs, grouped by underlying source file in `content/`. All numbers
below are read directly from each job's `validation.json` (`checks.coverage`),
`episode.json`, `stage_timings.json`/`validation.json.duration_plan.actual_duration_s`,
and `final_episode.mp4` file size on disk — nothing is estimated or invented.

Definitions used consistently below (matching `lib/sign_resolver.py::coverage_report`):
- **Total semantic concepts** = `total_sign_units` (each fingerspelled word counts once, not per letter)
- **Institutional coverage %** = `institutional_zho_coverage_pct` (ZHO only)
- **Supplementary coverage %** = `supplementary_observed_emirati_coverage_pct` (ESL Zayed only)
- These two are reported separately per the codebase's own explicit design (see `_note` field in every coverage report) — never combined into one blended number.

## Candidates surveyed

| Job ID | Topic (content file) | Duration (s) | Total concepts | ZHO | ESL Zayed | Fingerspell | Unsupported/Review | Institutional % | Supplementary % | mp4 exists / size |
|---|---|---|---|---|---|---|---|---|---|---|
| `013fbd2aa3f0` | test_g_high_coverage_family | 53.7 | 22 | 19 | 3 | 0 | 0 | 86.4% | 13.6% | yes / 2,875,671 B |
| `6fccd88afffa` | test_h_long_showcase | 125.2 | 29 | 15 | 5 | 9 | 0 | 51.7% | 17.2% | yes / 6,905,456 B |
| `bdff1892c9da` | test_h2_showcase_part2 | 91.2 | 20 | 7 | 3 | 9 | 1 unsupported | 35.0% | 15.0% | yes / 4,886,858 B |
| `96b5271e6215` | test_e_general_vocab_daily_habits | 63.2 | 16 | 5 | 7 | 3 | 1 review-required | 31.2% | 43.8% | yes / 3,808,371 B |
| `cc8c7402c026` | test_b_family_school | 26.3 | 8 | 6 | 1 | 1 | 0 | 75.0% | 12.5% | yes / 1,238,107 B |

## Per-candidate notes

### `013fbd2aa3f0` — test_g_high_coverage_family
- **Source**: "My Family and My Day at School" — father/doctor, mother/teacher, siblings, school routine.
- **Traceability quality**: overall_status `PASS` (the only PASS, not PASS_WITH_FALLBACK, in this sample) — every concept resolved to a real ZHO or ESL Zayed sign, zero fingerspelling, zero review flags.
- **Visual/render**: `final_episode.mp4` present, nonzero (2.9MB), 22 segments per traceability. (Not watched — file existence/size and segment count only.)
- **Pedagogical clarity**: simple, concrete family/school vocabulary, high clarity.
- **Technical story**: shows the system at its cleanest — 100% renderable, no gaps.
- **Demo risk**: LOW technically, but it does not exercise the fallback/fingerspelling/UNSUPPORTED path at all — a panel that probes "what happens when a sign doesn't exist" gets no evidence from this run alone.

### `6fccd88afffa` — test_h_long_showcase
- **Source**: "A Day With My Family" — longest/most content-rich source sampled (family roles, school routine, weather, grandmother/farm/garden material appears to overlap test_h2).
- **Traceability quality**: `REVIEW_REQUIRED` overall; largest segment count (29 concepts, 20 verified) — richest traceability.md/traceability.json to walk through live.
- **Visual/render**: mp4 present, 6.9MB (largest), longest duration (125s).
- **Pedagogical clarity**: good — covers family, school, and weather in one coherent narrative.
- **Technical story**: exercises all three tiers (ZHO 15, ESL Zayed 5, fingerspell 9) in one run — the single richest demonstration of the full authority hierarchy.
- **Demo risk**: longest run time (125s duration, ~369s pipeline build time) risks losing a live audience's attention if played in full; no genuine UNSUPPORTED/REVIEW item to show the "honest failure" path explicitly (all fallbacks succeeded as fingerspelling).

### `bdff1892c9da` — test_h2_showcase_part2 — **RECOMMENDED PRIMARY**
- **Source**: "A Day With My Family (Part 2)" — weather, school activities, exam success, visiting grandmother's farm/garden.
- **Traceability quality**: clean, complete chain verified directly (see `docs/TRACEABILITY_EXAMPLES.md` Example 1: HOT -> ZHO institutional sign, full chain from source span to rendered segment). Also contains a **genuine UNSUPPORTED case** (word "ON", Arabic "على", fingerspelling failed on an unmapped letter "ى") that the validator surfaced explicitly in `review_required.md` rather than silently dropping — this is real, live-observed evidence of the system, not a fabricated example.
- **Visual/render**: mp4 present, 4.9MB, 91s duration, 20 rendered segments.
- **Pedagogical clarity**: high — everyday narrative (weather, school, family pride, visiting grandmother).
- **Technical story**: the single unit "Academic Success" (u03) alone demonstrates ZHO, ESL Zayed, fingerspelling, AND an honest UNSUPPORTED flag in six consecutive words — the most complete single-slide illustration of the entire resolver hierarchy and its failure-honesty guarantee found in this survey.
- **Demo risk**: LOW-MODERATE — the UNSUPPORTED item must be framed correctly (as evidence of honesty/no-hallucination, not as a bug) or a lay panel could read it as "broken."

### `96b5271e6215` — test_e_general_vocab_daily_habits
- **Source**: "Daily Habits and Character" — routines, patience, "not lose hope" idiom.
- **Traceability quality**: `REVIEW_REQUIRED`; contains a genuine REVIEW_REQUIRED case: "NOT LOSE HOPE" — no verified lexical sign AND Arabic terminology translation was not usable, flagged rather than guessed.
- **Visual/render**: mp4 present, 3.8MB, 63s duration.
- **Pedagogical clarity**: more abstract vocabulary (character traits, idioms) — harder for a lay panel to instantly recognize signs for, compared to concrete family/school nouns.
- **Technical story**: highest supplementary (ESL Zayed) coverage in the sample (43.8%) — good secondary evidence that the ESL Zayed tier is doing real work, not just a placeholder.
- **Demo risk**: MODERATE — abstract idiomatic content is a harder sell visually/pedagogically than concrete vocabulary; only 1 review-flagged item versus bdff1892c9da's cleaner "one unit, four tiers" illustration.

### `cc8c7402c026` — test_b_family_school
- **Source**: same family/school opening as test_g/test_h, shorter, only 1 unit included.
- **Traceability quality**: `PASS_WITH_FALLBACK`, smallest/simplest run (8 concepts).
- **Visual/render**: mp4 present, 1.2MB, 26s (shortest) — fastest to play live if time is tight.
- **Pedagogical clarity**: highest (very short, simple family sentence).
- **Technical story**: minimal — good backup for "safe, fast, always-works" fallback demo, not a strong technical showcase.
- **Demo risk**: LOW but thin — not enough content to showcase the full hierarchy.

## Recommendation

**PRIMARY hero: `bdff1892c9da` (test_h2_showcase_part2 — "A Day With My Family (Part 2)")**
Justification: it is the only candidate in this sample that combines (a) a clean, fully
verifiable ZHO institutional chain (documented in `docs/TRACEABILITY_EXAMPLES.md`), (b)
real ESL Zayed supplementary usage, (c) fingerspelling fallback usage, and (d) a
genuine, live-observed UNSUPPORTED gap that the system flagged honestly instead of
hallucinating a sign or silently dropping the word — all within one manageable 91-second,
20-segment video. This directly demonstrates the panel's stated core interest:
hallucination-prevention and honest limitation-flagging, not just a high coverage number.

**BACKUP hero: `6fccd88afffa` (test_h_long_showcase — "A Day With My Family")**
Justification: richest single run (29 concepts, all three tiers represented, largest
rendered video), useful if the panel wants to see the system handle more content and a
longer, more complete narrative — trade-off is longer runtime and no explicit
UNSUPPORTED/REVIEW case of its own to point to (all gaps in this run were resolved via
fingerspelling successfully).

**Honesty note on fallback evidence**: real ESL Zayed usage and real fallback/gap cases
were found across multiple jobs in this survey (not fabricated) — see `bdff1892c9da`
(UNSUPPORTED "ON") and `96b5271e6215` (REVIEW_REQUIRED "NOT LOSE HOPE") in particular.
No candidate in this 100%-ZHO-coverage category (`013fbd2aa3f0`) was chosen as primary
specifically because it does not exercise or prove the fallback path at all.
