# Avatar retargeting — handoff for a new session

Paste this whole file as your first message in a new session to resume where this one left off.

## Context

Side-experiment off the MoE case study prototype (see `Brief/` and `MOI-Task/` in the project root, and `data/zho/coverage_report.md`) — testing whether a cartoon/rigged avatar could stand in for the real ZHO signer clips, driven by MediaPipe keypoints. Not part of the required build order; explore only as far as it stays useful.

## What's proven to work

- **MediaPipe Holistic extraction** (pose + both hands + 468-point face mesh) runs locally on CPU, ~30fps on an M1 Pro. Use `mediapipe==0.10.14` — current pip release `1.0.1` crashes natively on this machine (Metal/GPU graph-service fault in its new Tasks API); the legacy `mp.solutions` API in `0.10.14` works cleanly.
- **Active-window trimming**: ZHO clips are ~10s but the actual sign is only ~2-3s in the middle; `scripts/spike_find_active_window.py` auto-trims to the real active window using first/last frame with a hand detected.
- **Temporal smoothing matters a lot.** Raw per-frame MediaPipe output is visibly jittery undrawn; EMA smoothing (~alpha 0.25) on pose/hand/face channels fixes it.
- **Fixed per-clip scale, not per-frame.** The camera is static in these clips; recomputing body/limb size fresh every frame from noisy landmark positions makes the character visibly pulse. Compute a scale constant once (median shoulder width across the clip) and hold it fixed.
- **Screen-left/right mirroring**: MediaPipe labels landmarks anatomically (the subject's own left/right), which is mirrored vs. screen position for a normal forward-facing (non-selfie) camera. Confirmed empirically on the alif clip. Swap when mapping to a canvas.
- **Current working procedural renderer**: `scripts/spike_cartoon_avatar.py` — draws a simple flat-shape character (circle head, capsule limbs, real palm+finger hand shapes, real tracked eyebrows/eyes/mouth from the face mesh) directly from keypoints every frame. Just simplified: no headwear/beard/glasses (was tried, decided it wasn't reaching the target style and cost debugging time better spent elsewhere). This is the safe fallback — it can't "look broken" because it's not fitting rigid art to arbitrary motion, just drawing shapes at wherever the tracked points are.

## What was attempted and where it stands: rigid-art rigging

Tried driving actual generated character art (kandura/ghutra Emirati-styled) instead of drawn shapes, using pivot-point attachment + rotation + scaling. Real progress, real unresolved gaps:

- `scripts/spike_rigged_render_v2.py` — the current (best) version. Uses a proper 2D affine transform matrix per piece (rotate+scale+translate from two local pivot points to a target world position/angle/length) via `PIL.Image.transform(AFFINE)`, rather than hand-rolled trigonometry (which had real bugs — see git history / prior session for the debugging story if needed).
- Confirmed working: clean shoulder/elbow attachment, no gaps, bone-length scaling matched to real tracked proportions.
- **Not yet fixed**: hand orientation. Should use real tracked wrist→index-finger-base vector (MediaPipe hand landmarks 0 and 5) the same way arm segments use two pivot points — this was identified as the likely cause of "still looks wrong" on the last review but not completed before this session ended. The code has a placeholder (`h_prox[0]+30`) instead of real orientation data — fix that first.
- **Source art problem, not a code problem**: every attempt to get clean reusable art assets (ChatGPT sheet, Gemini sheet) hit real issues — grid/coordinate labels baked into the pixels, checkerboard backgrounds baked into JPEGs (no real alpha), inconsistent proportions between separately-drawn parts, low resolution when cropped from a composite sheet. An exact asset spec was written and handed to the user (rest-pose convention: every limb drawn perfectly vertical, fixed canvas size, fixed pivot pixel positions, one file per part, **no grid/label/ruler overlay baked into the art**) — worth checking if better assets exist before continuing rigging work.
- **Pivot-marking tool**: a working interactive tool exists for hand-clicking exact pivot coordinates on any asset set, published at (check with the user for the current artifact URL — it was live in the prior session). The rigging script already reads a `PIVOT_JSON` env var and prefers manual coordinates per piece over auto-detection, so real pivot data drops in without further code changes.

## Session 2 additions (2026-08-19)

Built a full captioned lesson video (`scripts/spike_render_captioned_lesson.py`) - 29 real ZHO segments, English+Arabic captions (via `arabic_reshaper`+`python-bidi`+PIL/SFArabic.ttf - `cv2.putText` cannot shape Arabic correctly, confirmed by inspection, produces genuinely garbled output not just stylistically rough), real ffmpeg crossfades between segments. Fixed several real bugs found via user testing, each worth knowing about if this is picked up again:

- **Per-segment scale drift**: computing "fixed scale" independently per segment (each is now a separate short clip) let each one lock onto a different value, so the character visibly changed size at every cut. Fixed with a two-pass detect-then-render architecture: detect all segments first, compute one global scale from the pooled data, render everyone against that shared value.
- **Same bug, position**: identical root cause for X/Y position - each segment's real signer stood wherever they happened to in their own source clip. Fixed the same way - compute each segment's anchor (median neck/shoulder-center), pick one global target, shift every segment's skeleton by a constant offset before rendering. Real measured shifts were up to 38px horizontal, 30px vertical - this was a substantial, real bug, not a minor one.
- **Uncanny hand-morph frames**: linear interpolation across a detection gap between two very different real handshapes (open hand vs. fist) passes through physically implausible in-between finger positions. Added a shape-distance check (`hand_shape_distance` in `spike_cartoon_avatar.py`) - if the two endpoints are too different, hold+fade the last known pose instead of interpolating toward a shape it was never really moving through.
- **Known unfixed limitation, not a bug**: signs that genuinely bring the hand close to/overlapping the face (e.g. "Looking") render poorly - the flat-shape outline+fill approach creates visual clutter exactly when two shapes are meant to nearly toutouch. Confirmed via the real source footage that the hand position itself is correct (that's the real signed content); the rendering just doesn't handle close overlap gracefully. Flagged, not solved.
- **MediaPipe vs YOLO-pose vs OpenPose researched** (not just asserted): YOLO-pose tested directly on this machine - body-only, 17 COCO keypoints, no hands/face, and slower (5.2fps CPU-default) than MediaPipe (30fps) on the same clip. Published comparisons found via web search: body-pose accuracy is genuinely mixed/context-dependent across tools (no clean winner), but MediaPipe's dedicated hand model is consistently reported as more accurate than OpenPose's general-purpose hand output. One source found worth reading directly if this comes up again: a paper titled "Evaluation of Pose Estimation Systems for Sign Language Translation" (arxiv 2604.24609) - evaluates pose systems for exactly this use case, not generic human-pose benchmarks.

**Real untapped capability - partially addressed before session end.** MediaPipe Holistic tracks 543 keypoints/frame (33 body + 42 hand + 468 face); the renderer originally used ~8 + 42 + 14 of those. Added real smile/frown mouth curvature (derived from mouth-corner position relative to mouth center - `smile` in `face_metrics()`) and eye width (inner/outer corner distance, not just openness) - both using landmarks that were already being extracted or are immediate neighbors of ones that were. Now ~8 + 42 + 18. Still far from exhausting the 468 available face points (no cheek/jaw contour, no per-lip-segment shape, no asymmetric brow) - a further pass here remains the highest-value next step for visual quality if this is picked up again, but the mouth was flat-line-only before this session and now has real shape, which was the most noticeable gap.

## Recommended next step

1. Check whether the user has better source art (following the spec above) before writing more rigging code.
2. If continuing rigging: fix hand orientation using real tracked wrist/index-base landmarks (see above) — this was the identified next bug, not yet fixed.
3. If not continuing rigging: the simplified procedural renderer (`spike_cartoon_avatar.py`) is the safe, working fallback for demo purposes — no further work needed there unless requested.

## Key files

```
scripts/spike_cartoon_avatar.py       # procedural renderer, simplified, working
scripts/spike_rigged_render_v2.py     # matrix-based rigged renderer, real bug: hand orientation
scripts/spike_extract_avatar_parts.py # extracts parts from a composite sheet (ChatGPT-style, real alpha)
scripts/spike_extract_gemini_sheet.py # extracts parts from a JPEG composite (Gemini-style, flood-fill bg removal)
scripts/spike_find_active_window.py   # auto-trims a ZHO clip to its active-sign window
data/zho/spike_mediapipe/avatar_parts/  # extracted art pieces (quality varies, see notes above)
```
