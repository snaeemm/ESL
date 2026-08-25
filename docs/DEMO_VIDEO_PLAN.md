# Standalone Demo Video Plan

**Status: video artifact ready — using existing processed hero output, no new recording needed.** `outputs/webapp_jobs/bdff1892c9da/final_episode.mp4` (4.9MB, 91.2s, confirmed present and playable via `ffprobe`) is the real, already-rendered hero episode ("A Day With My Family Part 2") and is sufficient as the standalone video artifact for submission. The full screen-recorded/narrated walkthrough described in the shot list below was considered but not produced — the live UI is instead documented via static screenshots (see `docs/DEMO_CANDIDATE_COMPARISON.md` / submission evidence zip) of the key states: landing/input, results/Lesson (video playback), Sign Plan (ZHO/ESL Zayed/fingerspell badges), Review (review-required + UNSUPPORTED flag), Traceability, and Technical Details, all captured against the live webapp for job `bdff1892c9da`.

Purpose: a short screen-recorded fallback video (does not depend on live internet or a live demo working on the panel day). This document is a plan only — the video itself is not produced here.

**Target length:** 3.5–4.5 minutes.
**Recording setup:** local machine, webapp running at `localhost:5173` + backend at `localhost:8000`, screen capture at 1080p, no audio narration recorded live (add narration in post per script below, or present live narration during panel playback).

## Shot list

| # | Time | Shot | Screen / artifact used | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:15 | Title card | Static slide | "AI-Powered Sign Language Academic Video Generator — MoE AI Center of Excellence Case Study" |
| 2 | 0:15–0:45 | Paste source text | Create Lesson screen, paste mode, using `content/test_h2_showcase_part2.md` ("A Day With My Family Part 2") | "Step 1 — Source: verified academic/educational text (EN or AR)" |
| 3 | 0:45–1:05 | Configure & generate | Create Lesson screen — duration selector, review-mode toggle, Generate button click | "Step 2 — Configure duration & review mode, then Generate" |
| 4 | 1:05–1:35 | Live pipeline stages | Progress screen, real stage events streaming (SOURCE→UNDERSTAND→STRUCTURE→GENERATE→VALIDATE→SIGN VIDEO) | "Every stage is real — no simulated progress bar" |
| 5 | 1:35–2:10 | Play the video | Results screen, Lesson tab, play `final_episode.mp4` for job `bdff1892c9da` | "Step 3 — Arabic Sign Language video with captions" |
| 6 | 2:10–2:40 | Validation / coverage | Results screen, Review tab — ZHO / ESL Zayed / combined coverage numbers, academic vs sign-language review split | "Deterministic validation — coverage reported honestly, never blended" |
| 7 | 2:40–3:20 | Traceability | Results screen, Traceability tab, filter to show one VERIFIED_SIGN (ZHO), one ESL_ZAYED, one FINGERSPELL, and the "ON" UNSUPPORTED row from unit u03 | "Every rendered sign traces to its source span and its authority" |
| 8 | 3:20–3:50 | Sign Plan tab, provenance badges | Results screen, Sign Plan tab, showing ZHO/ESL Zayed(supplementary)/Fingerspell badges side by side | "Institutional (ZHO) vs supplementary (ESL Zayed) vs fallback — never conflated" |
| 9 | 3:50–4:15 | Fallback / honest limitation | review_required.md excerpt or Review tab showing the "ON" UNSUPPORTED flag | "Genuine gaps are flagged, never hidden or invented" |
| 10 | 4:15–4:30 | Closing card | Static slide | "Local AI only · Falcon-H1-7B via Ollama · Full source code + traceability in repo" |

## Narration recommendation

Keep narration terse and declarative, matching the on-screen text above almost verbatim — avoid ad-libbing new claims not backed by the artifacts shown. If recorded live during the panel instead of pre-scripted, the presenter should read directly from `docs/PRESENTATION_RUNBOOK.md`'s talking points for each shot.

## Real job/artifact used

Primary source: job `outputs/webapp_jobs/bdff1892c9da/` (source `content/test_h2_showcase_part2.md`) — chosen because unit `u03` ("Academic Success") uniquely demonstrates all three authority tiers (ZHO, ESL Zayed, fingerspell) plus one genuine UNSUPPORTED flag in a single unit, per `docs/TRACEABILITY_EXAMPLES.md`. If `docs/DEMO_CANDIDATE_COMPARISON.md`'s PRIMARY hero differs from this job, prefer the selected hero for shots 2/5 (source paste + video playback) and keep `bdff1892c9da` for shots 7/9 (traceability/fallback) since it is the strongest evidence of the full hierarchy working end to end.

## Constraints honored

No live internet dependency (all shots are local webapp / local files). No PPTX produced here. No new video generation required beyond what's already in `outputs/`.
