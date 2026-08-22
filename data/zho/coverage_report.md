# ZHO Sign Language Dictionary — Indexing & Coverage Report

**Scope:** Brief Section 2, Build order step 1. Indexing/download of the ZHO (Zayed Higher Organization) UAE Sign Language Dictionary, plus a coverage report for Episode 1 ("Cells," Grade 6 Science Ch.3). Nothing beyond this was built — no backend/frontend scaffolding.

Source: https://www.za.gov.ae/en/Sign-Language-Dictionary/UAE-Sign-Language-Categories

---

## 1. Executive summary

- **Full dictionary indexed:** 1,143 entries across 21 categories, via a working (undocumented) JSON API — no browser automation needed.
- **All needed clips downloaded:** 36/36 (100%) — the 35-entry Alphabets set (fingerspelling fallback) + the 1 direct match for the Episode 1 term list.
- **Episode 1 term coverage: 1/24 direct (4%).** This matches the brief's own prediction exactly — ZHO is general-vocabulary, not science-domain, so 23/24 terms (cell, membrane, nucleus, mitochondria, cytoplasm, organelle, function, protect, energy, wall, plant, animal, structure, small, contain, produce, living, organism, body, part, example, difference, compare) have zero direct coverage and must be fingerspelled.
- **Signer identity — the important finding:** the dictionary is signed by (at least) **three distinct people**, not one:
  - **Signer A** (female) — Alphabets category only (35 entries).
  - **Signer B** (male) — 19 of 21 categories, **1,062 of 1,143 entries (92.9% of the whole dictionary)**. This is the de facto "primary" dictionary presenter.
  - **Signer C** (male, visibly different from B) — Sports category only (46 entries), not relevant to Episode 1.
- **Recommendation for Episode 1:** use **Signer A only** (fingerspelling for all 24 terms, including "inside" even though a direct Signer-B clip exists for it) to satisfy the brief's "presenter never visibly changes" rule. See §5.
- **One real technical blocker found and routed around** (§6): direct per-word detail pages are blocked by an edge WAF rule. Did not block indexing or download — a documented API workaround exists.
- **UAEU secondary dataset evaluated, not pursued further** (§7): the thesis PDF is openly downloadable, but the actual video corpus is not distributed alongside it — would require a direct request, exactly as the brief anticipated ("evaluate but do not block").

---

## 2. How the dictionary was indexed (method notes, for reproducibility)

The public site is a Sitecore SXA application. Two things are true simultaneously and matter for how `scripts/zho_index.py` works:

1. **Static HTML and the plain JSON search endpoint carry no video data** — the word cards are rendered by a client-side widget from a search-results JSON that only returns item paths (`Path`, `Url`, no title/video/thumb).
2. **Passing the SXA rendering-view GUID (`v` param) to the same endpoint returns full server-rendered card HTML per item**, which contains everything: word title, a direct signed Vimeo progressive-download MP4 URL, and a thumbnail image path. This was found by inspecting the search-results component's `data-properties` attribute in the category page's raw HTML and replaying its parameters against the endpoint directly with `curl`. No headless browser was needed.

Two bugs in the endpoint itself, discovered by testing rather than assuming:
- The documented-looking `page` parameter is **silently ignored** — every value returns the same first 20 results. The real pagination parameter is `e`, a 0-indexed item offset in steps of 20 (`e=0`, `e=20`, `e=40`, …). Found by trial after `page` produced identical results across values.
- Requesting `l=ar-AE` returns `Count: 1142` vs `Count: 1143` for `l=en` — a 1-item discrepancy between locales in the source data itself. Minor, flagged for awareness, not investigated further (out of scope for Section 2).

Video and thumbnail URLs are **locale-agnostic** — same physical Vimeo asset regardless of `l=en`/`l=ar-AE` — confirmed by direct comparison, so a single English-locale crawl fully indexes the dictionary.

---

## 3. Full catalog

`data/zho/catalog.json` — 1,143 rows, one per dictionary entry: `word_en`, `category`, `video_url`, `vimeo_id`, `thumb_path`, source item path/URL.

| Category | Entries |
|---|---:|
| Numbers | 116 |
| Professions and Jobs | 100 |
| Common Verbs | 96 |
| Health | 96 |
| Clothing and Toiletries | 89 |
| Attributes and Situations | 78 |
| Environment | 68 |
| Animals | 64 |
| Education | 61 |
| Sports | 46 |
| Ministries Departments | 42 |
| Household Items | 37 |
| Official Documents | 36 |
| Alphabets | 35 |
| Measurement Units | 33 |
| Popular Cuisines | 29 |
| Landmarks and Locations | 27 |
| Directions and Locations | 24 |
| Plants | 24 |
| Family | 23 |
| Colors | 19 |
| **Total** | **1,143** |

Data-quality notes worth carrying into the README's "known limitations" section:
- A handful of near-duplicate entries exist (e.g. "Second Wife" / "Second Wife-", two separate "Naphew" entries with different IDs) — the source dictionary itself, not a scraping artifact.
- Two English labels each cover two distinct Arabic letters, only distinguishable via the Arabic-locale title (the English transliteration alone collapses them): "Taa" ×2 is actually ت (regular taa) and ة (taa marbuta, titled "تاء مربوطة" in Arabic) — not ط, which has its own separate entry labeled "Tua." "Haa" ×2 is ه and ح, as labeled. Plus 4 hamza-position variants and the definite article "Al" — accounts for 35 Alphabet entries vs. 28 base Arabic letters. Practical implication: a fingerspelling matcher must resolve English labels against the Arabic-locale title, not assume a 1:1 English-label-to-letter mapping.

---

## 4. Episode 1 term coverage

Term list from Brief §3 (placeholder list, to be finalized against actual chapter text per the brief's own note).

| Term | Status | Notes |
|---|---|---|
| inside | **Direct match** | Category: Directions and Locations. Signed by **Signer B** (see §5 — recommend fingerspelling anyway for presenter consistency) |
| cell, membrane, nucleus, mitochondria, cytoplasm, organelle, function, protect, energy, wall, plant, animal, structure, small, contain, produce, living, organism, body, part, example, difference, compare | **No coverage — fingerspell** | 23/24 terms. Expected: ZHO is a general-vocabulary lexicon, not science-domain (brief §3 predicted exactly this) |

Matching method: exact case-insensitive match on `word_en` only. Raw substring matching was tried and discarded — it produced false positives with no semantic relationship (e.g. "cell" substring-matching "ex**cell**ent", "wall" matching "**al**" via word fragments). A real fallback matcher (stemming/lemmatization, e.g. "wall" ↔ "walls") should be built as part of the `generate` pipeline stage, not this indexing step — flagging for step 3 of the build order, not building it here.

**Conclusion: the fingerspelling/flagging fallback chain is not an edge case for this episode — it is the primary path.** 23 of 24 terms route through it. This validates the brief's architecture decision to build that fallback as a first-class part of the pipeline rather than an afterthought.

---

## 5. Signer identity — full findings

Per brief §2 task 3 ("tag each clip with signer identity — cluster by visual similarity if no metadata"): no metadata exists, so this was done by direct visual inspection (thumbnails sampled at first/middle/last position across all 21 categories, 63 images total, tiled into one contact sheet — `data/zho/signer_survey/contact_sheet.jpg`, legend in the same folder).

| Signer | Categories | Entries | Share |
|---|---|---:|---:|
| **A** (female, black abaya/hijab) | Alphabets only | 35 | 3.1% |
| **B** (male) | Animals, Attributes and Situations, Clothing and Toiletries, Colors, Common Verbs, Directions and Locations, Education, Environment, Family, Health, Household Items, Landmarks and Locations, Measurement Units, Ministries Departments, Numbers, Official Documents, Plants, Popular Cuisines, Professions and Jobs (19 categories) | 1,062 | 92.9% |
| **C** (male, visibly different from B — different face/skin tone, different headwear style) | Sports only | 46 | 4.0% |

**Implication for Episode 1:** the episode needs fingerspelling for 23/24 terms (Signer A, the only source for Alphabets) and has exactly one direct-word match, "inside" (Signer B). Per the brief's explicit rule ("fingerspell the gaps rather than switching to a different visible presenter mid-episode — the presenter should never visibly change person-to-person"), mixing A and B in one episode is disallowed even for one word. **Recommendation: fingerspell "inside" too, use Signer A as the sole presenter for Episode 1.** This is a one-word cost and keeps the episode fully compliant with the brief's own consistency rule.

**Implication beyond Episode 1 (worth a line on the production-path slide):** Signer B alone covers 92.9% of the entire dictionary across 19 of 21 categories. A general-vocabulary episode (not science-domain-heavy like Cells) would likely get strong direct-word coverage from a single consistent presenter with fingerspelling as a rare fallback rather than the primary path. Cells is close to a worst-case stress test for the fallback chain, which is exactly what it should be for a prototype demo — but it means Episode 1's near-total reliance on fingerspelling is a property of this specific episode's science vocabulary, not representative of general-content coverage.

**On synthetic unification (raised and considered, not adopted for the prototype):** the option of using a lightweight model to normalize different clips onto one consistent presenter was discussed. Two variants:
- *Face-swap/deepfake onto one real signer's likeness* — rejected. This is the exact approach the brief's own §6 already explicitly rejects for the prototype (cites the data-availability gap as the real blocker for neural sign generation generally); it additionally raises consent/likeness concerns specific to using real, identifiable ZHO government signers' faces in a synthesized composite, which is a materially different and worse problem than the brief's original concern.
- *Pose-driven stylized avatar retargeting* (extract hand/body keypoints from the real clips, drive a rigged avatar) — a genuinely better idea for later, since it doesn't impersonate any real person. But it's a nontrivial ML transformation sitting inside the "sign generation" stage, and for sign language specifically, retargeting errors change meaning — it would need its own accuracy validation before being defensible as traceable, which is real scope for a Phase 2 item, not this prototype. Recommend naming it explicitly on the production-path slide, next to the deepfake citation the brief already wants there.

For Episode 1 itself: deterministic single-signer selection (Signer A, fingerspelling) is simpler, needs no validation, and is already fully compliant — no model needed.

---

## 6. Technical blockers found (brief §2 task 5: flag immediately)

**Confirmed blocker:** direct navigation to any per-word detail page (`/en/Data/Sign-Category-Items/...`) is rejected by an edge WAF rule. Verified this is not specific to our target words — every URL containing the path segment `/Data/` is rejected identically (tested category-root URLs, other item URLs, with/without cookies, with/without referer headers — 100% rejection rate, "Request Rejected" / F5-style WAF page). **Does not block this project** — the JSON search API workaround (§2) bypasses these pages entirely and was used for 100% of indexing and download. Flagging it because it's a fragile dependency: if the search endpoint's undocumented `v`/`e` parameters ever change, there is no fallback path through the per-item pages as currently understood.

**No other blockers encountered.** No rate limiting observed across ~60 API calls (full 1,143-item index) + 36 video/36 thumbnail downloads (16MB total). Videos are direct, unauthenticated-at-our-end progressive MP4 downloads (redirect through `player.vimeo.com/external/...` to a signed `vimeocdn.com` URL) — no JS rendering required to obtain them, contrary to the brief's stated risk that this might be necessary.

---

## 7. UAEU secondary dataset — access evaluation

Per brief §2: "evaluate but do not block on it." `scholarworks.uaeu.ac.ae/all_theses/1022` — the thesis PDF itself has a direct, unauthenticated download link (standard Bepress repository pattern, no login/request wall). However, a thesis PDF documenting a 708-clip dataset does not mean the video files themselves are distributed there — institutional thesis repositories essentially never embed the underlying raw dataset, and no separate dataset link was found on the page. Consistent with the brief's own expectation: **likely requires a direct request to the author/university for the actual video files**, not a bulk download. Not pursued further per the brief's own instruction not to block on this — ZHO alone is sufficient to proceed with the prototype.

---

## 8. Usage rights (per brief §2, "don't skip this")

ZHO is an official Abu Dhabi government educational resource (za.gov.ae). As instructed: **usage terms should be formally verified with ZHO before any deployment beyond this prototype/demo context.** This is being carried into the README's limitations section near-verbatim per the brief.

---

## 9. Files produced

```
scripts/zho_index.py            # full catalog indexer (stdlib only, no deps)
scripts/zho_download.py         # downloads Alphabets + episode-term matches
data/zho/catalog.json           # 1,143-entry full dictionary index
data/zho/download_manifest.json # per-clip download record + term match map
data/zho/clips/<category>/*.mp4     # 36 downloaded clips (16MB)
data/zho/thumbs/<category>/*.jpg    # 36 thumbnails
data/zho/signer_survey/contact_sheet.jpg + legend.txt  # visual signer-ID evidence
data/zho/coverage_report.md     # this file
```

Both scripts are re-runnable idempotently (skip files already on disk) and use only the Python standard library — no environment setup needed for this step.

---

## 10. Addendum: MediaPipe avatar-retargeting feasibility spike (side experiment, out of scope)

Prompted by a mid-session question about whether a lightweight local model could retarget ZHO clips onto a stylized avatar (see §5's "pose-driven avatar" discussion). This was a bounded feasibility test only — not part of the pipeline, not built into anything.

**Setup:** `scripts/spike_mediapipe_avatar.py`, MediaPipe Holistic (pose + both hands), run locally via `uv run`, no cloud calls.

**A real bug hit and resolved:** the current pip release, `mediapipe==1.0.1`, removed the legacy `mp.solutions` API in favor of a new Tasks API. That new API's `HolisticLandmarker`/`HandLandmarker` crash natively on this machine (`Check failed: service_ Service is unavailable` inside `TensorsToDetectionsCalculator`, a Metal/GPU graph-service registration fault). Reproduced identically across Python 3.14 and 3.11, and with the coding-environment's own process sandbox both on and off — ruled out as an environment restriction, confirmed as a mediapipe 1.0.1 regression. **Workaround:** pin `mediapipe==0.10.14` (still has `mp.solutions.holistic`) — runs cleanly, correctly picks up the real Metal GPU context (`GL version: 2.1 (2.1 Metal - 90.5), renderer: Apple M1 Pro`). Worth remembering if any future step reaches for mediapipe.

**Results, run against two clips (one per major signer, §5):**

| Clip | Pose detected | Hand(s) detected | Processing speed |
|---|---:|---:|---:|
| Alphabets/Alif (Signer A) | 250/250 (100%) | 40/250 (16%) | 32 fps (CPU only) |
| Directions/Inside (Signer B) | 250/250 (100%) | 60/250 (24%) | 30 fps (CPU only) |

**Verdict:** local, real-time-capable, CPU-only (no GPU/NPU needed) — confirms this is a genuinely local-deployable approach, consistent with the brief's local-inference requirement. Body pose tracking is fully reliable. Hand tracking — the channel that actually carries sign meaning — is not: only 16-24% of frames get a hand landmark set at all in these two clips. On frames where it does fire, quality is good (clean 21-point mesh per hand, visually accurate). The gap is consistency, not accuracy per detection — likely driven by hands dropping outside the tightly-framed detection region, self-occlusion (hands clasped together, common in ZHO's resting pose), and fast inter-sign motion. This is a solvable problem with more engineering (temporal interpolation between confident frames, tighter hand-region cropping, a higher-frame-rate source) but is real, nontrivial work — confirms this belongs on the Phase 2 slide as a named, evidence-backed direction, not as a prototype feature.

---

## 11. Recommendation / what this unlocks for step 2 of the build order

Episode 1 can proceed with: **Signer A (female presenter) as the sole on-screen signer, full fingerspelling for all 24 terms.** The Alphabets set (35 clips, all one signer, already downloaded) is sufficient for this. No further ZHO download work is needed to start the backend pipeline — stopping here per instructions to report back before touching backend/frontend.
