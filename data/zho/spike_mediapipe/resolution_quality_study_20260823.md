# MediaPipe Holistic Resolution Quality Study (640x360 vs 960x540)

Date: 2026-08-23
Scope: read-only research spike. No production code, clips, model, or renderer modified. Nothing committed.

## A. Dataset

Total clips in `data/zho/clips/`: **44**. Confirmed via `ffprobe` on every file (not the earlier "by-category" assumption — actual resolution does **not** cleanly follow category: `Education/school_2499aa36.mp4` and `Education/teacher_d88fb82a.mp4` are 640x360, not 960x540). Verified breakdown:

- 640x360: **37** clips (35 in `Alphabets/`, plus `Education/school_2499aa36.mp4`, `Education/teacher_d88fb82a.mp4`)
- 960x540: **7** clips (`Directions and Locations/inside_7dd910a8.mp4`, `Family/family_c022191d.mp4`, `Family/father_5aae07f0.mp4`, `Family/mother_5ffb35c4.mp4`, `Family/sister_c3ed9923.mp4`, `Health/morning_ba20af63.mp4`, `Professions and Jobs/doctor_9116db67.mp4`)

All 44 clips confirmed as exactly 250 frames @ 25fps / 10.00s duration.

Because the 960x540 group only has **7 clips total**, all 7 were used (below the spec's 8-12 target — used all available, as instructed). For the 640x360 group, 12 clips were sampled to vary one- vs two-handed signing, framing, and content type (2 word-signs + 10 alphabet letters spanning different hand shapes/motion):

| Clip | Category | Res | Duration | Frames |
|---|---|---|---|---|
| inside_7dd910a8.mp4 | Directions and Locations | 960x540 | 10.00s | 250 |
| family_c022191d.mp4 | Family | 960x540 | 10.00s | 250 |
| father_5aae07f0.mp4 | Family | 960x540 | 10.00s | 250 |
| mother_5ffb35c4.mp4 | Family | 960x540 | 10.00s | 250 |
| sister_c3ed9923.mp4 | Family | 960x540 | 10.00s | 250 |
| morning_ba20af63.mp4 | Health | 960x540 | 10.00s | 250 |
| doctor_9116db67.mp4 | Professions and Jobs | 960x540 | 10.00s | 250 |
| school_2499aa36.mp4 | Education | 640x360 | 10.00s | 250 |
| teacher_d88fb82a.mp4 | Education | 640x360 | 10.00s | 250 |
| alif_eb6b778b.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| baa_9cecc2c2.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| jeem_d2892800.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| laam_aa2d0805.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| meem_e6e69718.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| noon_26f6fa6d.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| raa_56ca7677.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| seen_3fba6afb.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| wow_9fdb14bb.mp4 | Alphabets | 640x360 | 10.00s | 250 |
| yaa_dbe4bc5c.mp4 | Alphabets | 640x360 | 10.00s | 250 |

**Total sampled: 19 clips (7 × 960x540, 12 × 640x360), 4,750 total analyzed frames.** This is below the spec's 16-24 general aim only in that the 960 group is capped at all-available (7); 19 is within the stated 16-24 target range overall.

Extraction: MediaPipe Holistic, `static_image_mode=False, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5`, run via `uv run --python 3.11 --with "mediapipe==0.10.14" --with opencv-python --with numpy python3 <script>`, matching `scripts/spike_normalize_and_detect.py`'s `run_holistic()`. Every frame of every clip was processed (no subsampling). Coordinates kept MediaPipe-native normalized ([0,1]); no pixel conversion except transiently for jitter math on delta between consecutive normalized wrist points (a Euclidean distance in normalized-coordinate space, dimensionless).

## B. Visibility Annotation Method

Per spec: a hand is **expected visible** in a frame when the corresponding POSE wrist landmark (15=left, 16=right) has `visibility > 0.5` AND lies within `[0,1]×[0,1]` frame bounds. This uses the pose model (separate from the hand model) as a semi-independent oracle.

**Spot-check finding (critical, visual, subjective observation clearly labeled as such):** this heuristic is unreliable for one-handed signs where the idle hand hangs at the signer's side. Manually inspected frames from `baa_9cecc2c2.mp4` (640x360, alphabet, right-hand-only sign) and `alif_eb6b778b.mp4` (640x360) show the left arm hanging naturally at the side, often overlapping the dark abaya/kandura sleeve — the pose model still reports the left wrist as "visible" with high confidence (it can localize the approximate joint position even when occluded/at rest), but there is no active left hand to detect because the signer is not using it. This produces a large number of "expected but not detected" left-hand frames that are **not** MediaPipe hand-detection failures — they are heuristic false positives from one-handed content. Frames viewed: `baa_9cecc2c2.mp4` (4 frames), `alif_eb6b778b.mp4` (3 frames), `inside_7dd910a8.mp4` (2 frames, two-handed sign, both hands raised and genuinely detected), `family_c022191d.mp4`, `school_2499aa36.mp4`, `doctor_9116db67.mp4` (1 idle/title-card frame each, hands down, consistent with lead-in framing).

Because of this, **left-hand visibility-conditioned numbers in this dataset are dominated by the one-handed-sign confound and should not be read as a resolution effect.** Right-hand numbers are far more trustworthy as a controlled comparison since nearly every sampled clip (in both groups) is right-hand-dominant or two-handed with an active right hand, giving a much larger and cleaner expected-visible denominator on that side.

## C. Raw Landmark Availability (% of ALL frames, uncontrolled for expected visibility)

| Group | Clips | Frames | Pose % | Left-hand % | Right-hand % | Face % |
|---|---|---|---|---|---|---|
| 960x540 | 7 | 1750 | 100.0 | 6.5 | 19.4 | 100.0 |
| 640x360 | 12 | 3000 | 100.0 | 3.6 | 18.9 | 100.0 |

Raw right-hand and pose/face rates are nearly identical across groups. Raw left-hand rate differs but this mostly reflects the alphabet subset's one-handed content, not resolution (see section G).

## D. Visibility-Conditioned Hand Detection (primary metric)

detected-when-expected = frames where pose wrist visibility>0.5 AND hand landmarks were actually returned, divided by frames where pose wrist visibility>0.5.

| Group | Left expected | Left detected-when-expected % | Right expected | Right detected-when-expected % |
|---|---|---|---|---|
| 960x540 | 136 | 80.9% | 427 | 78.2% |
| 640x360 | 383 | 27.9% | 545 | 96.7% |

The left-hand column is the confounded one described in section B — 640x360's low 27.9% is driven almost entirely by the 10 one-handed alphabet clips (baa, jeem, laam, meem, raa, seen, yaa, alif each show exactly 0.0% left-hand detected-when-expected, i.e. the idle hand was never once detected as a "hand" the whole clip, consistent with an idle/resting arm, not a detection failure on a genuinely-present hand).

**Right hand — the confound-controlled comparison** — shows 640x360 (96.7%) outperforming 960x540 (78.2%) in this sample. This is the opposite direction from a "lower resolution hurts detection" hypothesis, though with only 7 vs 12 clips this should not be read as proof higher-res hurts anything either — more likely it reflects that the alphabet clips have simpler, more centered, less occluded right-hand motion than some of the 960x540 word-sign clips (e.g. `father_5aae07f0.mp4` and `doctor_9116db67.mp4` show comparatively lower right-hand detection, 70.5% and 68.5%, likely due to hand-near-face or hand-near-body occlusion in those specific signs, not resolution).

Per-clip visibility-conditioned rates (right hand) — full table:

| Clip | Res | Right expected | Right det-when-exp % |
|---|---|---|---|
| inside_7dd910a8 | 960 | 61 | 57.4 |
| family_c022191d | 960 | 60 | 90.0 |
| father_5aae07f0 | 960 | 44 | 70.5 |
| mother_5ffb35c4 | 960 | 57 | 82.5 |
| sister_c3ed9923 | 960 | 72 | 93.1 |
| morning_ba20af63 | 960 | 41 | 90.2 |
| doctor_9116db67 | 960 | 92 | 68.5 |
| school_2499aa36 | 640 | 60 | 93.3 |
| teacher_d88fb82a | 640 | 60 | 96.7 |
| alif_eb6b778b | 640 | 38 | 97.4 |
| baa_9cecc2c2 | 640 | 40 | 100.0 |
| jeem_d2892800 | 640 | 55 | 98.2 |
| laam_aa2d0805 | 640 | 35 | 94.3 |
| meem_e6e69718 | 640 | 40 | 95.0 |
| noon_26f6fa6d | 640 | 44 | 97.7 |
| raa_56ca7677 | 640 | 42 | 97.6 |
| seen_3fba6afb | 640 | 47 | 97.9 |
| wow_9fdb14bb | 640 | 42 | 95.2 |
| yaa_dbe4bc5c | 640 | 42 | 97.6 |

**Two-handed-only sub-comparison** (clips where left_expected was substantial, i.e. genuinely two-handed content: `inside`, `family` at 960; `school`, `teacher` at 640): left-hand detected-when-expected averaged 88.8% (960, n=2) vs 82.9% (640, n=2). A small (n=2 per side) difference in the direction of lower resolution being slightly worse — noted as a mild, statistically unreliable signal, not treated as evidence given the sample size.

## E. Pose/Face Results

Pose and face landmarks were detected in 100% of frames in both groups, for all 19 clips, with no exceptions. This is expected: pose/face are large, high-contrast, centered targets relative to the frame in both resolution classes, and MediaPipe's holistic pipeline runs pose/face detection on the full frame rather than a hand-scale crop, so resolution differences in this range (640x360 vs 960x540) do not meaningfully affect them here.

## F. Tracking Stability / Jitter

Jitter proxy: frame-to-frame Euclidean displacement of the detected hand's landmark-0 (wrist) point in normalized coordinates, computed only across consecutive frames where the hand was actually detected. "Spike" = a single-frame displacement > 5x the clip's own median displacement.

Right-hand jitter medians (normalized-coordinate units, mean across clips):
- 960x540 group: mean of per-clip medians ≈ 0.0111 (range 0.0030–0.0145)
- 640x360 group: mean of per-clip medians ≈ 0.0073 (range 0.0014–0.0171)

640x360 clips show *lower* median frame-to-frame displacement on average, not higher — again the opposite of a "lower res = more jitter" hypothesis, though this likely mostly reflects that many alphabet signs are smaller, more static hand shapes (fingerspelling letters) versus some word-signs having larger sweeping motion, a content confound rather than a resolution effect.

Spike counts (frames with displacement > 5x clip median) were, if anything, somewhat more frequent per-clip in the 640x360 group (several alphabet clips showed spike counts of 13–17 out of ~40-57 detected-frame transitions) versus the 960x540 group (mostly 0–4, with two exceptions at 12 and 14). This is flagged as a genuine but **inconclusive** observation: with several clips having a very small median displacement (e.g. 0.0014–0.0021), the 5x-median threshold becomes hypersensitive — a small absolute jump reads as a large multiple of an already-tiny median. This is a known artifact of ratio-based spike thresholds on near-static data, not necessarily "worse tracking." No sustained-drift or track-loss patterns (large multi-frame excursions that don't revert) were observed in either group on manual review of the numeric traces; spikes were single-frame and reverted, consistent with typical single-frame noise rather than sustained mistracking.

No genuine "fast motion" clips in this sample showed sustained high displacement without reverting (i.e., no confusion between fast-motion and jitter was needed to resolve — sustained motion, where present, showed moderate not extreme per-frame displacement).

Continuity gaps (contiguous runs of "expected visible but not detected" frames) were similarly small and comparable in count across groups (mostly 0–3 runs per clip, i.e., detection dropout was intermittent/brief rather than one long dead zone), with the notable exception of `father_5aae07f0.mp4` (960x540, 6 right-hand gap runs) — a possible occlusion-heavy clip, not resolution-driven since it's in the higher-resolution group.

## G. Confounders

- **One- vs two-handed signs (primary confound, addressed above):** ~10 of 12 sampled 640x360 clips are one-handed alphabet fingerspelling signs; the 960x540 sample includes a mix, with several also effectively one-handed (father, mother, sister, morning, doctor all show left_expected ≈ 0–10, i.e. the pose model itself found essentially no plausible active left-hand region — likely genuinely one-handed word signs too). This means BOTH groups are largely one-handed in this small sample, which somewhat limits (but does not eliminate) the left-hand confound's ability to distort the group comparison, since it affects both groups.
- **Signer/framing:** different individuals appear across clips (varying framing, clothing color/sleeve coverage, distance from camera), which affects occlusion of the idle hand and could account for some of the visibility-heuristic false positives independent of resolution.
- **Content difference (alphabet vs word signs):** alphabet fingerspelling tends to be smaller-amplitude, more centrally framed, held-shape gestures; word signs can involve larger or more dynamic motion and occasionally hand-near-face/body occlusion (seen in `father` and `doctor`), which plausibly explains those two clips' comparatively lower right-hand detection rather than a resolution effect, since `doctor`/`father` are in the *higher*-resolution group.
- **Sample size:** 7 and 12 clips per group respectively is small; per-clip variance is visible in the data (e.g. right-hand detected-when-expected ranges 57–100% within each group), so group means should be read as indicative, not conclusive.

## H. Preprocessing Experiment

**Skipped.** Per spec section 7, this experiment is only warranted if the 640x360 group shows meaningful degradation in visibility-conditioned detection. The confound-controlled (right-hand) comparison in section D shows the 640x360 group performing *at or above* the 960x540 group (96.7% vs 78.2%), and jitter medians are also not worse for 640x360. No degradation was found, so no preprocessing experiment was run, and no clips were copied to a scratch directory for this purpose.

## I. Limitations

- Sample is 19 of 44 total clips (43%), constrained by the dataset's small size — especially the 960x540 group, which is exhausted at 7 clips (all available were used).
- The pose-wrist-visibility heuristic for "expected visible" is a reasonable but imperfect proxy; section B documents a specific, visually-confirmed failure mode (idle-hand false positives for one-handed signs) that dominates the left-hand numbers. Right-hand numbers are more trustworthy but not immune to the same class of error in principle.
- Visual spot-checks covered 6 clips / ~12 frames total, a small manual sample used to sanity-check the automated heuristic, not to independently re-derive ground truth for the whole dataset.
- Jitter "spike" flagging uses a fixed 5x-median ratio threshold, which is sensitive to near-zero medians (noted in section F) — treat spike counts as a rough signal, not a calibrated instability score.
- No inferential statistics (e.g. significance tests) were computed or should be inferred; differences reported are descriptive only, per instruction, given n=7 and n=12.
- This study did not test on any unseen/held-out evaluation set and made no changes to the production pipeline, model, or thresholds.

## J. Defensible Panel Statement

*"In a bounded 19-clip spot-check using the pipeline's own MediaPipe Holistic settings, pose and face detection were 100% reliable at both resolutions, and after controlling for the one-handed-sign confound via the active (right) hand, the 640x360 fingerspelling clips showed detection and stability at least as good as the 960x540 vocabulary clips — so this small sample gives no credible evidence that the lower-resolution alphabet clips are a materially weaker input for the extraction pipeline."*

## K. Classification

**NO MATERIAL EVIDENCE OF RESOLUTION-RELATED DEGRADATION**

Justification: pose/face detection is saturated (100%) in both groups. The primary, confound-controlled metric (right-hand visibility-conditioned detection, the far larger and more trustworthy of the two hand-side denominators) is higher for 640x360 (96.7%) than 960x540 (78.2%). Jitter medians are also lower (better) on average for 640x360. The one notable contrary signal — a small two-handed sub-comparison (n=2 per group) showing 640x360 slightly behind on left-hand detection — is far too small a sample to treat as evidence, and is itself entangled with the idle-hand visibility-heuristic artifact documented in section B. Overall, within this small sample, there is no credible signal that 640x360 source material materially harms MediaPipe Holistic extraction relative to 960x540.
