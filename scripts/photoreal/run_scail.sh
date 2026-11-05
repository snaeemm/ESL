#!/bin/bash
# Render one or more driving videos with SCAIL-2 (zai-org/SCAIL-2).
# usage: [FAST=1] [OV=5] [CACHE=1] run_scail.sh W H STEPS SEED TAG [TAG...]
#   FAST=1   Lightx2v step-distill LoRA, no CFG (guide 1, shift 1), plus the DPO hand LoRA
#   OV       frames of clean history carried between 49-frame segments (default 5)
#   CACHE=1  save every finished segment, so a killed run resumes where it stopped
# Expects SCAIL_HOME with code/ (SCAIL-2 repo + patches/), weights/, inputs/, out/.
cd "${SCAIL_HOME:-$HOME/scail}/code"
export SCAIL_STREAM_BLOCKS=${SCAIL_STREAM_BLOCKS:-16} PYTORCH_HIP_ALLOC_CONF=expandable_segments:True \
       TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1
W=$1 H=$2 ST=$3 SEED=$4; shift 4
LORAS=../weights/dpo_hands.safetensors GS=5 SH=3 TAGX=""
if [ "${FAST:-0}" = 1 ]; then
  LORAS=$LORAS,../weights/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank128_bf16.safetensors GS=1 SH=1 TAGX=_fast
fi
P="An Emirati man with glasses, a short black beard, white kandura, white ghutra and black agal performs sign language in a grey studio, with natural hands and clearly separated fingers, mouth closed and relaxed, plain loose kandura sleeves."
mkdir -p ../out
for T in "$@"; do
  O=../out/sign_${T}_${W}_st${ST}_s${SEED}${TAGX}.mp4
  [ -f $O ] && continue
  S=$(date +%s)
  SCAIL_SEG_CACHE=${CACHE:+../out/cache_$T} ../venv/bin/python generate.py --model SCAIL-14B --ckpt_dir ../weights \
    --scail_path ../weights/SCAIL-2-bf16.safetensors --target_w $W --target_h $H \
    --image ../inputs/ref.png --mask_image ../inputs/ref_mask.png \
    --pose ../inputs/drive_$T.mp4 --mask_video ../inputs/drive_mask_$T.mp4 --prompt "$P" \
    --sample_steps $ST --sample_guide_scale $GS --sample_shift $SH --sample_solver unipc --base_seed $SEED \
    --offload_model False --t5_cpu --segment_len 49 --segment_overlap ${OV:-5} \
    --lora_path $LORAS --lora_alpha 1.0 --save_file $O
  echo "$T ${W}x$H st$ST s$SEED$TAGX ok=$([ -f $O ] && echo 1 || echo 0) $(( $(date +%s)-S ))s $(date +%H:%M)" >> ../out/progress.txt
done
