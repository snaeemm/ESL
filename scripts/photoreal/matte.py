"""Cut the presenter out of every sign and put him on one fixed studio plate.

Pass 1 mattes every frame (BiRefNet portrait via rembg) and builds the plate
from the background pixels of all signs; pass 2 composites onto that plate,
so the background can no longer change shade or carry specks between chunks.
Usage: matte.py [TAG ...]   (default: every sign in $SCAIL_HOME/out)
Writes $SCAIL_HOME/clean/<TAG>.mp4 and clean/plate.png.
"""
import glob, os, subprocess, sys, time
import cv2, numpy as np
from PIL import Image
from rembg import new_session, remove

HOME = os.path.expanduser(os.environ.get("SCAIL_HOME", "~/scail"))
OUT = f"{HOME}/clean"
TRIM = {"21": 52}  # EXCELLENT: source clip ends with a badge graphic
os.makedirs(OUT, exist_ok=True)
sess = new_session("birefnet-portrait")


def frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return np.stack(out)
        out.append(f)


def alpha(f):
    m = remove(Image.fromarray(f[:, :, ::-1]), session=sess, only_mask=True, post_process_mask=False)
    return np.asarray(m, np.float32) / 255


srcs = sorted(glob.glob(f"{HOME}/out/sign_*_fast.mp4"))
tag = lambda p: os.path.basename(p).split("_")[1]
if sys.argv[1:]:
    srcs = [p for p in srcs if tag(p) in sys.argv[1:]]

acc = wsum = 0
clips = {}
for p in srcs:
    t0 = time.time()
    raw = frames(p)[:TRIM.get(tag(p), 10 ** 6)]
    al = np.stack([alpha(f) for f in raw])
    # light temporal smoothing so the cut-out edge doesn't shimmer
    al = np.concatenate([al[:1], al, al[-1:]])
    al = 0.25 * al[:-2] + 0.5 * al[1:-1] + 0.25 * al[2:]
    w = (1 - al) ** 4
    w[al > 0.05] = 0
    acc = acc + (raw.astype(np.float32) * w[..., None]).sum(0)
    wsum = wsum + w.sum(0)
    clips[tag(p)] = (raw, al)
    print(f"matted {tag(p)} {len(raw)} frames {time.time() - t0:.0f}s", flush=True)

plate = acc / np.maximum(wsum, 1e-6)[..., None]
hole = (wsum < 1).astype(np.uint8)
plate = cv2.inpaint(np.clip(plate, 0, 255).astype(np.uint8), hole, 15, cv2.INPAINT_TELEA)
plate = cv2.GaussianBlur(cv2.medianBlur(plate, 5), (0, 0), 3).astype(np.float32)
cv2.imwrite(f"{OUT}/plate.png", plate.astype(np.uint8))

for t, (raw, al) in clips.items():
    a = al[..., None]
    out = np.clip(raw * a + plate * (1 - a), 0, 255).astype(np.uint8)
    h, w = out.shape[1:3]
    pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{w}x{h}", "-r", "25", "-i", "-", "-c:v", "libx264", "-crf", "14",
                           "-pix_fmt", "yuv420p", f"{OUT}/{t}.mp4"], stdin=subprocess.PIPE)
    pr.stdin.write(out.tobytes()); pr.stdin.close(); pr.wait()
    print("composited", t, flush=True)
