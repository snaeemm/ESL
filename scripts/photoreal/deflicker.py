"""Smooth the brightness jumps at SCAIL segment joins.
Usage: deflicker.py IN.mp4 OUT.mp4

The jump is low-frequency and uneven across the frame, so each frame's blurred
(low-frequency) layer is replaced by a temporally smoothed one; fine detail
(fingers, face, fabric) is left untouched. Output is retagged to 25fps.
"""
import subprocess, sys
import cv2, numpy as np

src, dst = sys.argv[1], sys.argv[2]
SIG_XY, SIG_T = 40, 4.0
cap = cv2.VideoCapture(src)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f.astype(np.float32))
v = np.stack(frames)
low = np.stack([cv2.GaussianBlur(f, (0, 0), SIG_XY) for f in v])
r = int(3 * SIG_T)
w = np.exp(-0.5 * (np.arange(-r, r + 1) / SIG_T) ** 2)
pad = np.concatenate([low[:1].repeat(r, 0), low, low[-1:].repeat(r, 0)])
smooth = np.stack([np.tensordot(w / w.sum(), pad[i:i + 2 * r + 1], axes=1) for i in range(len(v))])
outv = np.clip(v - low + smooth, 0, 255).astype(np.uint8)
h, wd = v.shape[1:3]
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                      "-s", f"{wd}x{h}", "-r", "25", "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", dst],
                     stdin=subprocess.PIPE)
p.stdin.write(outv.tobytes())
p.stdin.close()
p.wait()
