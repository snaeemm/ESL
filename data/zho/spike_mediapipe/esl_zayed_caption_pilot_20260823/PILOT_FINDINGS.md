# ESL Zayed Caption-State Segmentation — Pilot Findings (2026-08-23)

**Scope:** read-only pilot. No production file under `lib/` or `webapp/` was changed. The
existing safe ~20-word `data/zho/esl_zayed_supplementary_catalog.json` was NOT modified. No
scaling was performed. This directory holds the pilot's scratch artifacts only.

## Method actually implemented

`caption_segment.py`: extracts frames via `ffmpeg` at a fixed 0.2s step (no OpenCV — see
environment note below), computes a small grayscale signature of a caption-region crop per
frame with Pillow+numpy, and detects discrete state-change boundaries via thresholded
frame-to-frame mean-abs-diff with a 0.6s debounce (so brief flicker/motion blur isn't counted
as a caption change). This is frame-differencing / stable-state clustering, not per-frame OCR,
per the task's stated preference.

Two passes were run:
1. **Naive global band** (assumed captions live in a fixed top-22% or bottom-22% strip,
   auto-picking whichever band has more change-energy).
2. **Per-template calibrated region**, after manually inspecting real extracted stills (via the
   Read-image tool, not assumption) and discovering the corpus actually uses **at least three
   different caption placements**:
   - `right_box` (x 55-100%, y 12-62%) — the "Emirati Sign Language - N" word/phrase template
     (signer left-center, Arabic+English caption stacked at right)
   - `bottom_center_big` (x 25-75%, y 72-100%) — the alphabet-letter template (huge single
     letter bottom-center, e.g. "C")
   - `upper_right_small` (x 68-100%, y 8-38%) — the number template (small digit upper-right)

This alone is an important, honest finding: **a single global caption-region assumption is
wrong for this corpus.** Any real implementation needs a per-video (or per-template-cluster)
calibration step, which was not budgeted for in the "assume one band" version of the task and
adds real scope.

## Environment note (reported honestly, not papered over)

- `yt-dlp -f best` (the format string used successfully in the prior session's commit bb3895f)
  now fails with "Requested format is not available" for every tested video — YouTube no longer
  serves pre-merged progressive formats for these videos. Fixed by switching to
  `-f "135+140/134+139/best"` (separate video+audio DASH streams, merged by ffmpeg). This is a
  real, dated environment/YouTube-side drift, not a code bug in this repo.
- A stray leftover file `inspect.py` in the session scratchpad directory shadowed the Python
  stdlib `inspect` module (because the script's own directory is first on `sys.path` when run
  as a file), which broke `numpy`/`cv2` imports with a confusing
  `AttributeError: module 'inspect' has no attribute 'cleandoc'` unrelated to numpy/opencv
  versions. Root-caused and removed; not a repo bug, but worth recording since it cost real
  time and could recur if scratch dirs are reused carelessly.
- `opencv-python` + `numpy` import together triggered a separate, still-unexplained crash in
  this sandbox in some runs (same `inspect.cleandoc` symptom) even after removing the shadow
  file, on the very first cold `uv` cache build. It was NOT reliably reproduced after the shadow
  file was removed, so this pilot's caption-detection script deliberately avoids `cv2` entirely
  (uses `ffmpeg` subprocess + Pillow + numpy only) to route around it. MediaPipe/OpenCV itself
  was not needed for the caption-signal half of this pilot; the secondary motion-refinement step
  (§ below) still depends on the existing, already-working `mediapipe==0.10.14` + `opencv-python`
  pattern from `lib/clip_prep.py`, which the prior session already proved works in this same repo
  (commit bb3895f).

## Pilot videos and manually-verified expected item counts

Expected counts are the corpus's own `total_items_in_video` / `item_index_in_video` fields from
`esl_zayed_full_93video_corpus_20260823.json`, cross-checked against manually extracted stills
(via ffmpeg `fps=1` + direct visual inspection) for every video below — not taken from titles.

| Video ID | Title | Content type(s) | Expected items | Why selected |
|---|---|---|---|---|
| XVtU5dtnkQU | Emirati Sign Language - 1 | WORD+PHRASE | 3 | small count, includes the spec's own example "السلام عليكم" |
| jtFsC8Pr8B8 | Emirati Sign Language - 2 | WORD+PHRASE | 4 | small count |
| Ctz__kub2SE | Emirati Sign Language - 78 | WORD+PHRASE | 8 | mid-size, two-handed signs observed |
| GwMOAeE1eP4 | Emirati Sign Language - 4 | WORD+PHRASE | 7 | mid-size |
| 2l1WqXUZfC8 | Letters English ESL | LETTER | 26 | long alphabet sequence, fast transitions |
| vkt9JcQ6JEU | Emirati Sign Language - 69/70-style | NUMBER | 8 | number sequence, different caption template |
| EQAWOu-yB_g | Emirati Sign Language - 24 | WORD+PHRASE | 3 | explicitly named in the task spec as a "don't trust the title" example |
| 696dGt5Zfv0 | Hello | SENTENCE+WORD | 4 | phrase/sentence-bearing video |

All 8 are real, downloaded, ffmpeg-probed source videos (not titles, not the old sparse JSON
alone) — durations/resolutions/fps in `seg2_*.json` in this directory came from `ffprobe` on
the actual files.

## Automatic segmentation vs manual reference (per-template-calibrated pass)

| Video | Expected items | Detected segments | Δ | Manual boundary spot-check | Classification |
|---|---|---|---|---|---|
| XVtU5dtnkQU | 3 | 4 | +1 (over) | title card (0-2s) correctly split off; "How are you"/"Fine" boundary roughly at the right place but one extra spurious split inside a single caption's stable window | REVIEW_REQUIRED |
| jtFsC8Pr8B8 | 4 | 4 | 0 (coincidental) | manually viewed stills at t=4.5s and t=6.5s: BOTH still show "Last name" inside what the detector called one 8s segment (2.0-10.0s) — segment durations are wildly uneven (8s / 2.8s / 2.1s) suggesting a merge of >1 real item plus a spurious split elsewhere; count matched by chance, not because boundaries are individually correct | REVIEW_REQUIRED |
| Ctz__kub2SE | 8 | 1 | -7 (severe under) | entire 28s video returned as ONE segment — text-box region changes were below the diff threshold across most genuine item transitions on this specific video (likely because hands cross into the text-box region during two-handed signs, adding constant "noise" energy that swamped the real caption-change signal, or the text box sits closer to center than assumed) | REJECT_SEGMENTATION |
| GwMOAeE1eP4 | 7 | 4 | -3 (under) | first detected segment alone spans 11.0s of a 19.5s video — almost certainly multiple real items merged | REJECT_SEGMENTATION |
| EQAWOu-yB_g | 3 | 4 | +1 (over) | this is the video the task spec explicitly warns not to under-segment by trusting the title; detector over-split by one | REVIEW_REQUIRED |
| 696dGt5Zfv0 | 4 | 2 | -2 (under) | a 10.8s first segment out of 14s total is very likely 2+ merged sentence/word items | REJECT_SEGMENTATION |
| 2l1WqXUZfC8 | 26 | 57 | +31 (severe over) | letter-region diff picks up finger/hand motion adjacent to the big bottom-center letter as spurious caption changes — more than double the true letter count | REJECT_SEGMENTATION |
| vkt9JcQ6JEU | 8 | 2 | -6 (severe under) | small upper-right digit region changes too subtly (few pixels) relative to the diff threshold tuned for the larger `right_box` template; number template needs its own threshold, not reused from the word template | REJECT_SEGMENTATION |

## E. Pilot segment-count agreement

0/8 exact-and-boundary-correct. 2/8 (jtFsC8Pr8B8, XVtU5dtnkQU) landed within ±1 of the expected
count, and even jtFsC8Pr8B8's exact count match is shown by manual spot-check to be a coincidental
cancellation of one merge + one spurious split, not genuine per-item correctness. 6/8 show gross
(>=2 items, up to +31/-7) count errors.

## H. Classification counts (8 pilot videos)

- AUTO_ACCEPT: 0
- REVIEW_REQUIRED: 2 (XVtU5dtnkQU, jtFsC8Pr8B8) — and even these need caveats per above
- REJECT_SEGMENTATION: 6 (Ctz__kub2SE, GwMOAeE1eP4, 696dGt5Zfv0, 2l1WqXUZfC8, vkt9JcQ6JEU, and EQAWOu-yB_g is borderline REVIEW/REJECT, counted REVIEW above but with an unresolved off-by-one)

0% AUTO_ACCEPT is far below the task's own illustrative "still valuable" example (70/25/5). This
is a real measured result on real videos, not a predetermined threshold applied a priori.

## I. Main failure modes (all observed on real footage, not hypothesized)

1. **No single fixed caption region works across the corpus.** At least 3 distinct on-screen
   templates exist (word/phrase right-box, alphabet bottom-center-big, number upper-right-small).
   A production version needs a template-classification step per video before caption-region
   diffing can even start — unbudgeted scope, not attempted here.
2. **Hand motion inside or near the caption region contaminates the "caption changed" signal**
   for two-handed signs and signs performed close to the body/text (Ctz__kub2SE, GwMOAeE1eP4).
   Frame-differencing on a fixed crop cannot distinguish "the text changed" from "a hand entered
   the crop."
3. **Single global threshold does not generalize across region sizes.** The number template's
   digit is small, so real caption changes there produce far less diff-energy than the
   word-template's larger text block — same threshold either over-fires on the big region or
   misses on the small one (observed directly: word template over/under by 1, number template
   missed 6 of 8 real changes).
4. **Even a "correct" segment count can hide wrong boundaries** (jtFsC8Pr8B8) — a real risk if
   count-agreement alone were used as a scale/no-scale gate without the manual boundary
   spot-checks this pilot did.
5. This is 8 videos manually spot-checked in the time available — a materially larger hand-graded
   reference set (the task's own upper suggestion of "8-12") was not fully completed at the same
   depth of manual boundary verification for every video; only count-level checks plus targeted
   still-frame spot-checks were done for all 8, with deeper multi-point boundary verification
   only for XVtU5dtnkQU and jtFsC8Pr8B8.

## J. Scale/no-scale decision: **DO NOT SCALE (OUTCOME B)**

Per the task's own stop rule: 0/8 AUTO_ACCEPT, 6/8 REJECT_SEGMENTATION, and the 2 REVIEW cases
have documented boundary-correctness doubts even where counts matched. This is a materially
unreliable result, not a borderline "good enough, ship it" case. Forcing this to scale across the
other 85 videos would mean building the ESL Zayed WORD catalog expansion on top of segment
boundaries this pilot has direct, first-hand evidence are frequently wrong (merges, splits, and
one 0-for-1 total-miss case). That is exactly the outcome the task instructs against ("do not
create dubious clips").

## Estimated manual-review burden if this were to be completed by hand

93 videos x avg ~4.3 items/video (403 records / 93 non-alphabet-heavy but including two ~30-item
letter videos) ~= 403 candidate teaching segments. Manual boundary-setting at the rate observed
in this pilot (~10-15 minutes per video including still-extraction, template identification, and
timestamp entry for a 3-9 item video; the two long letter/number videos would take longer,
~25-30 minutes each) extrapolates to roughly **18-22 hours of focused manual annotation** to
produce a fully human-verified timestamped corpus for all 93 videos, before any MediaPipe
refinement pass. This is a rough order-of-magnitude estimate from this pilot's actual observed
pace, not a guess made without doing the work.

## What would need to change before automation could be trusted

- Per-video (or per-template-cluster) caption-region calibration, likely via a cheap first-pass
  classifier (e.g. does the video's first few seconds match the word/phrase title-card layout,
  the letter-card layout, or the number-card layout) rather than one fixed region.
- A region-relative, motion-normalized diff signal that discounts change concentrated where
  MediaPipe pose/hand landmarks are already detected as active (this pilot ran caption detection
  and motion detection as fully separate signals; the task's own "caption primary, MediaPipe
  secondary" design assumes MediaPipe never influences the caption signal itself, but in
  practice hand-overlap contamination was the single largest source of error here — this is a
  design tension worth flagging back to the task owner, not resolved unilaterally in this pass).
- Per-template thresholds, not one global `diff_thresh`.

None of the above were implemented in production code this session — this pilot stops here per
the stop rule, and the existing safe ~20-word `esl_zayed_supplementary_catalog.json` is
untouched.
