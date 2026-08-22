# Avatar rigging asset spec

Goal: individual rest-pose pieces that `spike_rigged_render_v2.py` can
rotate/scale/translate onto real tracked motion via 2D affine transform,
matching the style of the reference image (flat vector illustration,
Emirati ghutra/agal/kandura, soft gradient shading).

The previous attempt (ChatGPT sheet, Gemini sheet) failed on these
specific defects - avoid all of them this time:
- grid/coordinate/ruler labels baked into the pixels
- checkerboard "transparency" baked into a JPEG (no real alpha channel)
- inconsistent proportions between separately-generated parts
- low resolution when cropped out of one big composite sheet

## Hard requirements, every piece

- **Real transparency**: PNG with an actual alpha channel, not a
  checkerboard pattern drawn as pixels. If your tool can't export real
  alpha, this whole approach won't work no matter how good the art looks.
- **One piece per file** - do not generate a composite sheet and crop it
  (this is what caused the low-res/inconsistent-proportion failures last
  time). Generate each file as its own image, same style prompt reused.
- **Straight rest pose**: every limb drawn perfectly vertical / neutral -
  no bend, no perspective foreshortening, arms straight down at the
  torso's sides, head facing forward. The rigging code supplies all the
  actual bend/rotation/angle from tracked motion; the source art must be
  "unposed" or every rotation will look wrong.
- **No overlay**: no grid lines, rulers, coordinate numbers, watermarks,
  or labels anywhere in the image.
- **Consistent proportions across every piece**: same head-to-shoulder
  width ratio, same limb thickness, same art style/line weight/shading
  approach in every single file - generate them in one session reusing
  the same style description, not across separate unrelated attempts.
- **Consistent canvas size and character scale** across all pieces (e.g.
  every file 800x800px, character drawn at the same relative scale) so
  the pieces compose back together at the right proportions without
  per-piece manual rescaling guesswork.

## Pieces needed (one file each)

1. **head_front.png** - head + face + ghutra + agal, facing forward,
   neutral expression, no beard/glasses unless you want them tracked
   separately.
2. **torso_kandura.png** - torso/kandura only, no arms, neck to hip,
   straight-on, matching the reference's shading/fold style.
3. **upper_arm_l.png** / **upper_arm_r.png** - shoulder-to-elbow segment,
   drawn straight vertical, kandura sleeve fabric.
4. **forearm_l.png** / **forearm_r.png** - elbow-to-wrist segment,
   straight vertical, sleeve tapering toward the wrist opening.
5. **hand_open.png**, **hand_fist.png**, **hand_point.png**, etc. - one
   file per distinct handshape actually used in the lesson signs (check
   `scripts/spike_render_captioned_lesson.py`'s SEGMENTS list for which
   signs are included), straight/neutral wrist orientation, skin tone
   matching the head.

## Pivot points (needed after generation, not part of the image itself)

Once real assets exist, pivot coordinates (where each piece attaches to
the next - e.g. exactly where the upper arm's elbow-end pixel sits) get
marked with the existing interactive pivot-marking tool from the prior
session (ask to have it republished if the artifact link has expired) and
fed into `spike_rigged_render_v2.py` via the `PIVOT_JSON` env var - the
rigging code already supports this, no code changes needed for that part.

## What's still a known bug in the rigging code, separate from art

`spike_rigged_render_v2.py` has a placeholder for hand orientation
(`h_prox[0]+30` instead of a real tracked direction vector) - this needs
fixing using the real wrist->index-base vector (MediaPipe hand landmarks
0 and 5) once real hand art exists to test it against. Not worth fixing
against placeholder/broken art first.
