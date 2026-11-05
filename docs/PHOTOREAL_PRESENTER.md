# Photoreal presenter: two approaches

The prototype (main README) renders the lesson with a procedural 2D avatar. This document covers the follow-up work: the same 24-sign lesson ("My Family and My Day at School") performed by a **photoreal presenter generated from a single photo**. The presenter is the author, Shahzeb Naeem, generated from his own photo with his consent.

Two approaches were tried. They differ in what drives the motion.

```
APPROACH A - keypoints                         APPROACH B - real signer video
real signer clip (ZHO / ESL Zayed)             real signer clip (ZHO / ESL Zayed)
  -> MediaPipe Holistic keypoints                -> person mask
  -> 2D avatar / skeleton video                  + one photo of the presenter
  -> video model restyles it photoreal           -> SCAIL-2 reads motion straight from
     (Seedance, LTX-2.3 IC-LoRA)                    the video pixels, no keypoints
```

The front half of the pipeline (source -> sign plan -> which ZHO / ESL Zayed clip) is unchanged in both. Only the final rendering step differs. The keypoint avatar remains the prototype's renderer and still runs.

## Approach A: keypoints -> avatar -> photoreal

| Video | What it shows |
|---|---|
| [`demo/MOE_Prototype_Lesson_Demo.mp4`](../demo/MOE_Prototype_Lesson_Demo.mp4) | The original keypoint avatar lesson |
| [`demo/approach_A_keypoints/01_avatar_vs_seedance.mp4`](../demo/approach_A_keypoints/01_avatar_vs_seedance.mp4) | **Best of A.** Avatar (left) restyled into a photoreal presenter by Seedance 2.0 mini, a commercial model (right) |
| [`demo/approach_A_keypoints/02_real_signer_vs_seedance_vs_ltx_keypoints.mp4`](../demo/approach_A_keypoints/02_real_signer_vs_seedance_vs_ltx_keypoints.mp4) | Real signer vs Seedance vs the best free option, LTX-2.3 with keypoint control |

**Verdict:** the best-looking result overall (Seedance: crisp fingers, one continuous take), but anything the avatar gets wrong, the video model faithfully copies. A 2D skeleton also cannot tell the palm from the back of the hand, so palm orientation, which changes a sign's meaning, can come out inverted (seen with LTX).

## Approach B: real signer video -> SCAIL-2

| Video | What it shows |
|---|---|
| [`demo/approach_B_real_video/01_scail2_full_lesson.mp4`](../demo/approach_B_real_video/01_scail2_full_lesson.mp4) | **Best of B.** Full lesson, 24 signs, 61 s, 896x512, captioned, clean studio background |
| [`demo/approach_B_real_video/02_real_signer_vs_seedance_vs_scail2.mp4`](../demo/approach_B_real_video/02_real_signer_vs_seedance_vs_scail2.mp4) | Real signer vs Seedance (approach A) vs SCAIL-2 (approach B), full lesson |
| [`demo/approach_B_real_video/03_scail2_vs_wan_animate2.mp4`](../demo/approach_B_real_video/03_scail2_vs_wan_animate2.mp4) | SCAIL-2 vs Wan-Animate-2 on FATHER, WAKE UP and WALK |

**Verdict:** the most faithful to the real signs. Where the avatar and the real signer differ, SCAIL-2 follows the real signer: FATHER is signed under the chin (Seedance: across the mouth), SCHOOL with palms up (Seedance: palms to camera). Weak spots: occasionally soft fingers, and a visible pop at each cut because every sign is rendered separately.

### How B works

```
real signer clip + person mask + one photo of the presenter + short appearance prompt
  -> SCAIL-2 (14B), 8 steps, Lightx2v step-distill LoRA (no CFG) + DPO hand LoRA,
     896x512, seed 7, 49-frame segments with the last frames carried into the next
  -> scripts/photoreal/matte.py      presenter cut out (BiRefNet portrait) and composited
                                     onto one fixed studio plate built from all signs
  -> scripts/photoreal/deflicker.py  temporal smoothing of the low-frequency layer only
  -> scripts/photoreal/assemble_lesson.py  captioned lesson
```

The prompt only describes appearance (glasses, beard, kandura, ghutra, grey studio). The motion, including every handshape, comes from the real signer's video.

## Model comparison (qualitative, judged against the real signer)

| Model | Approach | Result |
|---|---|---|
| **SCAIL-2** (open, MIT) | B | **Selected.** Handshape and palm orientation matched on every sign checked |
| Seedance 2.0 mini (commercial API) | A | Best picture and smoothness; copies avatar errors |
| Wan-Animate-2 14B distilled (open, Apache-2.0) | B | Close to SCAIL-2 on 3 signs, worse over 8; on SISTER the hand pulled the glasses off and the face changed |
| LTX-2.3 + union-control IC-LoRA (open) | A | Sharp picture; palms inverted on several signs |
| Wan-Animate pose retarget (open) | A | Invents fingers |

These are visual judgements on this lesson, not a benchmark. Correct handshape and palm orientation were weighted first, then face, clothing and smoothness.

## What was hard

- **Hardware.** All of approach B ran locally on one shared AMD Ryzen AI Max workstation (ROCm, 64 GB shared CPU/GPU memory). [`PHOTOREAL_SCAIL2_PATCHES.md`](PHOTOREAL_SCAIL2_PATCHES.md) lists the six changes that made a 14B video model fit. Wan-Animate-2 additionally needed its compiled flex-attention replaced by three exact SDPA calls merged by log-sum-exp, and an fp32/bf16 mismatch fixed (it produced all-black output).
- **Background.** Separate renders drifted in background shade and picked up specks; fixed by matting onto one fixed plate.
- **Transitions.** Frame interpolation between signs warped the arms and crossfades looked like overlaps, so plain cuts are used.
- **Source artefacts.** The EXCELLENT source clip ends with an on-screen badge that the model redrew as a fake logo; that clip is trimmed at frame 52.

## In progress: one-take render

[`scripts/photoreal/build_drive.py`](../scripts/photoreal/build_drive.py) joins all 24 real-signer clips (6-frame blends) into one 1,434-frame driving video, and SCAIL-2 renders the whole lesson as a single take (36 segments, 9 frames of history between them), so face, lighting and motion carry through from sign to sign. [`finish.py`](../scripts/photoreal/finish.py) then applies the plate, deflicker and captions. The first segment (FATHER into DOCTOR) is continuous with no jump; the full render is not finished yet.

## Scripts

| File | Purpose |
|---|---|
| `scripts/photoreal/run_scail.sh` | Render driving videos with SCAIL-2 (per sign or one take; resumable) |
| `scripts/photoreal/build_drive.py` | Build the one-take driving video, masks and caption spans |
| `scripts/photoreal/matte.py` | Clean studio background for per-sign renders |
| `scripts/photoreal/deflicker.py` | Low-frequency temporal deflicker |
| `scripts/photoreal/assemble_lesson.py` | Captioned lesson from per-sign renders |
| `scripts/photoreal/finish.py` | Plate + deflicker + captions for a one-take render |

Model weights and the presenter photo are not included.
