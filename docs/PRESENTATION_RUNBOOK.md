# Presentation Runbook — MoE Panel

## Flow

1. **Slides 1–2** (`docs/SLIDE_CONTENT.md`) — proof of working prototype, architecture, AI/deterministic boundary, model choices. ~3 min.
2. **Live website walkthrough of hero lesson** — Create Lesson → paste source → configure → Generate → Progress stages streaming live. Use the PRIMARY hero job (see `docs/DEMO_CANDIDATE_COMPARISON.md`). ~3 min.
3. **Play the video** — Results screen, Lesson tab. ~1 min.
4. **Traceability** — Results screen, Traceability tab; walk one VERIFIED_SIGN (ZHO) row, one ESL_ZAYED row, one FINGERSPELL row. Reference the concrete example in `docs/TRACEABILITY_EXAMPLES.md` (job `bdff1892c9da`, unit u03, word "HOT"/"I"/"DO WELL"). ~2 min.
5. **ZHO / ESL Zayed / fingerspell provenance** — Sign Plan tab, point at the three distinct badges; state explicitly: "ESL Zayed is supplementary and never overrides a good ZHO sign — it is never shown as institutionally verified." ~1 min.
6. **Fallback example** — Review tab or `review_required.md`, the "ON" UNSUPPORTED flag from unit u03 — "a genuine gap, flagged not hidden." ~1 min.
7. **Slides 3–4** — sign-authority hierarchy recap, strongest metrics, security/data handling, deployment/scalability, human-in-the-loop, honest limitations, production roadmap. ~3 min.
8. **Production path** — close on README §15 phases. ~1 min.

Target total: ~15 minutes, leaving time for panel Q&A using `docs/PANEL_DEFENSE.md`.

## 4-tier fallback plan (must not depend on live internet)

- **Tier A — Live site.** `localhost:5173` + `localhost:8000` + local Ollama running, generate live or replay a pre-generated job. Fully local; no internet dependency for core inference. (Clip download for any *new* sign not already cached under `data/zho/clips/` does need internet — mitigate by using an already-cached hero job, not a fresh source, for the live demo.)
- **Tier B — Pre-generated job loaded.** If live generation is flaky, load an existing completed job directly on the Results screen (History tab → pick the hero job ID) — no pipeline run needed, purely reading `outputs/webapp_jobs/<id>/*.json` and playing the cached video.
- **Tier C — Screen recording.** Play the standalone demo video per `docs/DEMO_VIDEO_PLAN.md` if the webapp cannot run at all on-site (no laptop setup, no Ollama, etc).
- **Tier D — Raw video + screenshots.** If no playback device works, present `final_episode.mp4` file directly (any video player) plus printed/screenshotted `traceability.md` and `review_required.md` excerpts from the hero job.

Each tier downgrades gracefully and none requires internet connectivity at presentation time (Tier A's one caveat is noted above and mitigated by pre-caching the hero job's clips before the panel).

## Pre-panel checklist

- Confirm hero job's clips are already cached in `data/zho/clips/` (run once locally beforehand, offline-safe afterward).
- Confirm `ollama serve` and the Falcon model are pulled and working on the presentation machine, if attempting Tier A live generation.
- Have `outputs/webapp_jobs/<hero-id>/final_episode.mp4` and `review_required.md` saved to a USB/local copy as Tier D backup.
- Print or screenshot the traceability example from `docs/TRACEABILITY_EXAMPLES.md` as a physical backup.
