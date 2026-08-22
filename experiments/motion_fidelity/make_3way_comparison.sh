#!/bin/bash
# Builds a 3-way side-by-side comparison: real signer footage | avatar
# BEFORE | avatar AFTER, for the same 9-clip sequence
# extract_and_render_long.py uses, in the same order, so they stay frame-
# synced. Run this AFTER extract_and_render_long.py has produced
# long_before.mp4/long_after.mp4.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT_DIR="outputs/motion_fidelity_test"
NORM_DIR="data/zho/spike_mediapipe/lesson/norm"
CLIPS=(03_teacher 04_explain 08_examine 14_looking 16_find 17_circle 19_center 25_grows 27_answer)

LIST_FILE=$(mktemp)
for c in "${CLIPS[@]}"; do
  echo "file '$(pwd)/${NORM_DIR}/${c}.mp4'" >> "$LIST_FILE"
done

ffmpeg -y -v error -f concat -safe 0 -i "$LIST_FILE" -c:v libx264 -crf 18 -pix_fmt yuv420p "${OUT_DIR}/long_real.mp4"
rm -f "$LIST_FILE"

ffmpeg -y -v error \
  -i "${OUT_DIR}/long_real.mp4" \
  -i "${OUT_DIR}/long_before.mp4" \
  -i "${OUT_DIR}/long_after.mp4" \
  -filter_complex "[0:v]pad=iw+4:ih:0:0:color=black[v0];[1:v]pad=iw+4:ih:0:0:color=black[v1];[v0][v1][2:v]hstack=inputs=3[v]" \
  -map "[v]" "${OUT_DIR}/long_comparison_3way.mp4"

echo "Wrote ${OUT_DIR}/long_comparison_3way.mp4 (real | before | after)"
