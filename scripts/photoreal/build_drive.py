"""Join the real signers' clips (and their person masks) into one continuous
driving video, so the whole lesson can be rendered as a single take.

Usage: build_drive.py NAME XF TAG [TAG...]
  Reads   inputs/drive_<TAG>.mp4 and inputs/drive_mask_<TAG>.mp4
  Writes  inputs/drive_NAME.mp4, inputs/drive_mask_NAME.mp4, inputs/NAME.json
  XF      crossfade length in frames between consecutive clips (0 = hard join)
NAME.json records the frame span of each sign, used later for captions.
"""
import json, os, sys
import cv2, numpy as np

os.chdir(os.environ.get("INPUTS", "inputs"))
name, xf, tags = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
TRIM = {"21": 52}  # EXCELLENT: the source clip ends with an on-screen badge


def read(path, n):
    cap, out = cv2.VideoCapture(path), []
    while len(out) < n:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(f, (960, 540), interpolation=cv2.INTER_AREA).astype(np.float32))
    return out


vid, msk, spans = [], [], []
for t in tags:
    n = TRIM.get(t, 10 ** 6)
    v, m = read(f"drive_{t}.mp4", n), read(f"drive_mask_{t}.mp4", n)
    k = min(len(v), len(m))
    v, m = v[:k], m[:k]
    if vid and xf:
        for i in range(xf):
            a = (i + 1) / (xf + 1)
            vid[-xf + i] = vid[-xf + i] * (1 - a) + v[i] * a
            msk[-xf + i] = np.maximum(msk[-xf + i], m[i])  # union of both people's masks
        v, m = v[xf:], m[xf:]
    spans.append([t, len(vid) - (xf if spans else 0), len(vid) + len(v)])
    vid += v
    msk += m

for f, frames in ((f"drive_{name}.mp4", vid), (f"drive_mask_{name}.mp4", msk)):
    w = cv2.VideoWriter(f + ".tmp.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 25, (960, 540))
    for fr in frames:
        w.write(np.clip(fr, 0, 255).astype(np.uint8))
    w.release()
    os.system(f"ffmpeg -nostdin -y -loglevel error -i {f}.tmp.mp4 -c:v libx264 -crf 12 -pix_fmt yuv420p {f}"
              f" && rm {f}.tmp.mp4")
json.dump(spans, open(f"{name}.json", "w"))
print(name, len(vid), "frames")
