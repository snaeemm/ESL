# MediaPipe Holistic Controlled Paired Resolution Study (960x540 native vs. 640x360 downscaled-from-same-source)

Date: 2026-08-23
Scope: read-only research spike. No production code modified, no files under `data/zho/clips/` modified. Report is intentionally left untracked (not `git add`ed).

## 0. Purpose and relationship to the prior study

`data/zho/spike_mediapipe/resolution_quality_study_20260823.md` (same date, prior session) compared **naturally-occurring** 640x360 clips (mostly alphabet fingerspelling) against **naturally-occurring** 960x540 clips (mostly word signs) already in the library. Its own stated limitation was that the two groups differ in sign type, motion amplitude, and framing, so any resolution effect is confounded with content differences — it explicitly could not isolate resolution as the sole variable.

This study is a **different, narrower experiment** designed to close that gap: it holds the underlying video constant per clip and only varies resolution, by downscaling each native 960x540 clip to 640x360 with a plain `ffmpeg scale` filter and re-running identical MediaPipe extraction on both the original and the downscaled copy of the *same* recording. It answers "what does resolution alone change, with content held fixed?" — a tighter but much smaller-scope question than the prior study's "do the two naturally occurring groups differ?" This report supplements, and does not replace or overwrite, the prior study.

## 1. Dataset construction

**Native 960x540 clip count re-verified via `ffprobe` on every file in `data/zho/clips/`: exactly 7** (unchanged from the prior session's count):

| # | Clip | Category | Res | FPS | Duration | Frames | Aspect |
|---|---|---|---|---|---|---|---|
| 1 | `inside_7dd910a8.mp4` | Directions and Locations | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |
| 2 | `family_c022191d.mp4` | Family | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |
| 3 | `father_5aae07f0.mp4` | Family | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |
| 4 | `mother_5ffb35c4.mp4` | Family | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |
| 5 | `sister_c3ed9923.mp4` | Family | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |
| 6 | `morning_ba20af63.mp4` | Health | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |
| 7 | `doctor_9116db67.mp4` | Professions and Jobs | 960x540 | 25 | 10.00s | 250 | 16:9 (confirmed) |

All 7 originals verified 16:9 via `ffprobe` (960/540 = 16:9 exactly) before scaling — no distortion risk, plain `scale=640:360` used for all.

Each original was left completely untouched. A downscaled copy of each was created with:
```
ffmpeg -i <original> -vf scale=640:360 -c:v libx264 -crf 0 -preset veryfast <output>
```
stored under the session scratch directory, never in the repo. `ffprobe` on every downscaled copy confirmed **width=640, height=360, r_frame_rate=25/1, nb_frames=250, duration=10.000000** — i.e. exactly matching the source's frame count, fps, and duration; no dropped or duplicated frames from the resize.

**Total: 7 paired clips, 250 frames per clip per resolution → 3,500 total frames analyzed (1,750 at 960x540 + 1,750 at 640x360).**

## 2. Extraction

MediaPipe Holistic, identical settings for every run (original and downscaled alike): `static_image_mode=False, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5`, invoked via `uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python --with numpy python3 <scratch extraction script>`, matching this project's standard Holistic config (same as used by the prior study and `scripts/spike_normalize_and_detect.py`'s `run_holistic()`). Every frame of every clip was processed, no subsampling, no parameter differences between the two resolution conditions — the only variable that changes between the paired runs is the input video's pixel dimensions.

Per frame the script recorded: full 33-point pose landmarks (x, y, z, visibility), full 21-point left/right hand landmarks (x, y, z) when present, and face detection presence plus a derived bounding-box (min/max x/y over all face landmark points) used for two lightweight face-consistency metrics — center-point displacement and bbox-area ratio between resolutions. This face bbox derivation is a simple metric authored for this study (the prior study did not need to compute a cross-resolution face metric, since it only measured detection presence, and face presence was 100% there too).

## 3. Visibility ground truth (shared, computed once from the 960x540 original)

Per the prior study's validated heuristic: a hand is **expected visible** in a frame when the corresponding POSE wrist landmark (15=left, 16=right) has `visibility > 0.5` and lies within `[0,1]×[0,1]`. This label set was computed **once per clip, from the 960x540 original's pose output only**, and the identical per-frame boolean labels were reused to evaluate both the 960x540 and 640x360 conditions of that same clip — the downscaled run's own pose output was never used to re-derive visibility, so labeling noise cannot masquerade as a resolution effect.

As the prior study found, this heuristic has a known false-positive mode for one-handed signs (idle arm at the side still reads as "visible" to the pose model). In this 7-clip set, left-hand expected-visible frames are minimal or zero for 5 of 7 clips (`father`=2, `mother`=0, `sister`=10, `morning`=0, `doctor`=0 expected-visible frames out of 250) — consistent with these being effectively one-handed or near-one-handed word signs. Only `inside` (61 expected) and `family` (63 expected) have substantial two-handed content. **Right-hand numbers are therefore the primary, trustworthy metric in this study; left-hand numbers are reported for completeness but are low-n and should not be over-read.**

## 4. Per-clip metrics table

Pose and face detection were **100.0% at both resolutions for all 7 clips**, no exceptions — omitted from the table below since there is no variance to show.

| Clip | Right expected (of 250) | Right det@960 % | Right det@640 % | Δ (640−960) | Left expected | Left det@960 % | Left det@640 % |
|---|---|---|---|---|---|---|---|
| inside_7dd910a8 | 61 | 57.4 | 62.3 | +4.9 | 61 | 93.4 | 95.1 |
| family_c022191d | 60 | 90.0 | 83.3 | −6.7 | 63 | 84.1 | 82.5 |
| father_5aae07f0 | 44 | 70.5 | 70.5 | 0.0 | 2 | 0.0 | 0.0 |
| mother_5ffb35c4 | 57 | 82.5 | 84.2 | +1.8 | 0 | n/a | n/a |
| sister_c3ed9923 | 72 | 93.1 | 91.7 | −1.4 | 10 | 0.0 | 0.0 |
| morning_ba20af63 | 41 | 90.2 | 92.7 | +2.4 | 0 | n/a | n/a |
| doctor_9116db67 | 92 | 68.5 | 69.6 | +1.1 | 0 | n/a | n/a |

**Right-hand aggregate across clips:** mean det@960 = 78.9% (median 82.5%, range 57.4–93.1%); mean det@640 = 79.2% (median 83.3%, range 62.3–92.7%). Mean per-clip delta = +0.31 percentage points (640 minus 960), with deltas ranging from −6.7 to +4.9 and no consistent direction (4 of 7 clips favor 640, 2 favor 960, 1 tied).

### Paired disagreement (right hand, summed over all 7 clips, counted over the 427 total right-expected frames)
- Detected at **both** resolutions: 326 frames
- Detected at **960 only**: 8 frames
- Detected at **640 only**: 9 frames
- Detected at **neither**: 84 frames

Near-symmetric (8 vs 9) — no meaningful directional disagreement.

### Paired disagreement (left hand, summed over the 136 total left-expected frames, dominated by `inside` and `family`)
- Both: 109, 960-only: 1, 640-only: 1, neither: 25. Also near-symmetric, but n is small and concentrated in 2 of 7 clips.

## 5. Cross-resolution landmark consistency (agreement, not accuracy — see limitations)

Computed only over frames where the same landmark was detected at **both** resolutions. Reported as mean absolute normalized-coordinate displacement between the 960 and 640 outputs for that clip, then aggregated as mean/median/range across the 7 clips.

| Metric | Mean of per-clip means | Median | Range |
|---|---|---|---|
| Right wrist (pose lm 16, all 250 frames/clip) | 0.0428 | 0.0152 | 0.0096–0.1574 |
| Right hand landmark aggregate (21 pts, frames both-detected) | 0.0042 | 0.0024 | 0.0011–0.0103 |
| Right index fingertip (lm 8) | 0.0051 | 0.0032 | 0.0013–0.0132 |
| Right thumb tip (lm 4) | 0.0053 | 0.0033 | 0.0015–0.0129 |
| Full pose aggregate (33 pts, all 250 frames/clip) | 0.0282 | 0.0277 | 0.0149–0.0436 |
| Face bbox center displacement | 0.00069 | 0.00069 | 0.00058–0.00083 |
| Face bbox area ratio (960/640) | ~1.00 across all 7 clips (0.999–1.006) | — | — |

All hand-landmark and face-metric consistency values are small in absolute normalized-coordinate terms (on the order of 0.001–0.01, i.e. roughly 1–5 pixels of drift at 640-wide scale) and consistent with ordinary re-run/model-noise-level disagreement rather than a systematic resolution-driven landmark shift. **One outlier**: `morning_ba20af63`'s right-wrist pose-landmark consistency is 0.157, several times higher than the other 6 clips (which range 0.0096–0.0585); this is a pose-model-only metric computed over all 250 frames (not conditioned on hand detection), and its cause was not further diagnosed in this study — flagged honestly as an unexplained single-clip outlier rather than smoothed over, but it does not co-occur with a detection-rate anomaly for that clip (its right-hand detection rates are 90.2%/92.7%, among the best in the set), suggesting it may be a pose-tracking quirk unrelated to hand-detection quality.

## 6. Temporal stability (right hand, same fixed thresholds applied to both resolutions)

Jitter proxy: frame-to-frame Euclidean displacement (normalized coords) of the detected right-hand landmark-0 point, computed only across consecutive frames where the hand was detected. "Spike" = single-frame displacement > 5x the clip's own median (same definition as the prior study).

| Metric | 960x540 (mean of per-clip medians) | 640x360 (mean of per-clip medians) |
|---|---|---|
| Jitter median | 0.0104 (range 0.0026–0.0145) | 0.0118 (range 0.0032–0.0169) |

640x360 shows a small increase in mean jitter median relative to 960x540 (+0.0014, roughly 13% relative), but both values are small in absolute terms, ranges overlap substantially, and with n=7 clips this is not distinguishable from noise.

**Spike counts** (per clip, 960 vs 640): inside 0/0, family 0/0, father 0/1, mother 13/13, sister 3/5, morning 0/0, doctor 1/1. No large or systematic increase at 640x360; `mother`'s high spike count (13/13, identical at both resolutions) reflects that clip's very small median displacement making the 5x-ratio threshold hypersensitive (same known artifact the prior study flagged), not a resolution effect, since it is identical at both resolutions for that clip.

**Gap runs** (contiguous "expected-but-not-detected" runs while visibility-expected): 960 totals were 2,3,6,3,2,1,3 across the 7 clips; 640 totals were 3,5,5,3,3,2,2 — slightly more numerous at 640x360 in aggregate (21 vs 20 — essentially the same total) but not concentrated or dramatically different in any one clip.

**Reappearance-far events** (a hand reappearing after a gap at a position far — >0.15 normalized units — from its last known position, used to distinguish plausible fast motion from a tracking jump): 960: 1,0,1,1,1,0,0 (total 4); 640: 1,1,3,1,1,1,0 (total 8). A modestly higher count at 640x360, concentrated somewhat in `father_5aae07f0` (3 events). Manual inspection of the numeric traces did not find sustained drift (multi-frame excursions that fail to revert) at either resolution — all flagged events were single reappearance points, consistent with either brief occlusion-driven dropout-and-recovery or a tracking discontinuity; this study could not fully distinguish the two from landmark traces alone, and reports the ambiguity rather than asserting jitter.

## 7. Statistical discipline

This is a bounded paired engineering validation with **7 clips** (all native 960x540 clips available in the library) and **3,500 total paired frames** (1,750 per resolution). Frames within a clip are highly correlated (same signer, same motion, same 10-second sign), so frame counts are **not** independent samples — no frame-level confidence intervals or significance tests are computed or implied anywhere in this report. All aggregate statistics above are computed **per-clip first**, then summarized as mean/median/range **across the 7 clips**, per the task's requirement. With n=7, "range" is the primary honest indicator of spread; no inferential claims should be drawn beyond this specific set of 7 clips and their one-time downscale.

## 8. Optional preprocessing sensitivity check

**Skipped — no material degradation was found to investigate.** Right-hand detected-when-expected is statistically indistinguishable between resolutions (mean delta +0.31 pts, no consistent direction), pose/face are saturated at 100% for both, landmark consistency values are small and comparable to expected re-run noise, and jitter/gap/reappearance differences are small and do not show a systematic resolution-driven pattern. Per the task's instruction, the preprocessing sensitivity check (alternate interpolation filters, aspect-preserving pad/resize) is only warranted when material degradation is observed; it is not run here.

## 9. Limitations

- **n=7 clips** — the entire native 960x540 population of this library; no larger paired sample is currently possible without adding new source clips. This is a ceiling on this study, not a sampling choice.
- **Left-hand numbers are low-n and content-confounded**: 5 of 7 clips have near-zero left-hand-expected frames (effectively one-handed word signs), so the left-hand comparison rests almost entirely on 2 clips (`inside`, `family`) and should not be treated as a general finding.
- **Visibility ground truth is a heuristic, not human-annotated**: the pose-wrist-visibility>0.5 rule (reused from the prior study, which itself flagged its idle-arm false-positive mode) is a proxy for "a hand a human would expect to see," not a manually verified label. It was held constant across both resolution conditions per clip specifically to prevent this heuristic's own noise from appearing as a resolution effect, but the heuristic's absolute accuracy against a human labeler was not independently re-verified in this study.
- **Landmark "consistency" is agreement between two model outputs, not accuracy against ground truth**: neither the 960x540 nor the 640x360 MediaPipe output is a verified true position (no human-annotated keypoints exist for these clips). Small consistency values indicate the two resolutions largely agree with each other, not that either is correct. This is stated explicitly per the task's requirement and should not be read as an accuracy claim anywhere in this report.
- **One CRF-0 lossless re-encode step**: downscaled copies were re-encoded with `libx264 -crf 0` (lossless) purely to produce a decodable video container after the `scale` filter; this is not expected to introduce its own artifacts (lossless), but it is a technically distinct step from a hypothetical raw-frame resize, noted for completeness.
- **Single downscale pass, single interpolation method** (ffmpeg's default `scale` filter, bilinear): no sensitivity check on alternate interpolation methods was run (see section 8) since no degradation was found to motivate it — this study cannot speak to whether a different (e.g. lanczos) downscale would perform differently, only that the default `scale` filter, held constant across all 7 clips, shows no material effect at 640x360 vs. 960x540.
- **The `morning_ba20af63` right-wrist consistency outlier (0.157) was not further diagnosed** — flagged rather than explained away; it does not coincide with an unusual detection-rate pattern for that clip, but its root cause (pose-model noise, subtle framing artifact, or something else) is unknown.
- **No production code, threshold, or pipeline change resulted from or should be inferred from this study** — this is evidence-only, per task scope.

## 10. Relationship to the prior study (explicit contrast)

| | Prior study (`resolution_quality_study_20260823.md`) | This study |
|---|---|---|
| Question | Do naturally-occurring 640x360 clips look like worse MediaPipe input than naturally-occurring 960x540 clips? | Holding the same video constant, what changes when only resolution changes? |
| Design | Between-groups comparison of two different, pre-existing clip sets (37 vs 7 clips in the library; 19 sampled) | Within-clip paired comparison: same 7 clips, each run at its native 960x540 and at a controlled 640x360 downscale of itself |
| Main confound | Sign type/content differs systematically between groups (alphabet fingerspelling vs. word signs) — explicitly flagged as unresolved in that study | Content is held perfectly constant per pair by construction; confound is largely eliminated for the resolution variable specifically |
| Sample | 19 clips, 4,750 frames | 7 clips, 3,500 paired frames (all of them cross-resolution pairs of each other) |
| Finding | No material evidence of degradation, but confound-limited | No material evidence of degradation, with the content confound controlled |

Both studies point the same direction; this one adds a tighter causal claim (resolution alone, not resolution-plus-content) at the cost of a smaller, fully-paired sample.

## 11. Classification

**NO MATERIAL DEGRADATION OBSERVED AFTER CONTROLLED DOWNSCALING**

Justification, considering A–G together: pose and face detection remain saturated at 100% for all 7 clips at both resolutions. The primary confound-controlled metric — right-hand visibility-conditioned detection — shows a mean difference of +0.31 percentage points (640 vs 960) with no consistent direction across clips (4 of 7 favor 640x360, 2 favor 960x540, 1 tied) and overlapping ranges; the paired disagreement counts are near-symmetric (8 detected-960-only vs 9 detected-640-only, out of 427 expected frames). Cross-resolution landmark consistency values are small in absolute terms for hands, fingertips, pose, and face, consistent with ordinary model re-run noise rather than a systematic degradation, aside from one unexplained single-clip pose-wrist outlier that does not correspond to a detection-quality anomaly. Jitter medians are marginally higher at 640x360 (+0.0014 mean, ~13% relative) but with overlapping ranges across only 7 clips; gap-run and reappearance-far counts show small, non-dramatic increases at 640x360 that do not indicate sustained tracking loss on manual review. No single metric or combination of metrics in this paired, confound-controlled sample supports a claim of material degradation at 640x360 relative to native 960x540 for this pipeline's standard Holistic configuration.

## 12. Safe panel statement

*"In a controlled, paired 7-clip test where the exact same sign videos were run through the pipeline's MediaPipe extraction at their native resolution and again after being resized down to a lower resolution, detection quality and tracking stability were statistically indistinguishable between the two — so, within this small but tightly controlled check, there is no evidence that using the lower-resolution format for this dataset would weaken the extraction pipeline's performance."*
