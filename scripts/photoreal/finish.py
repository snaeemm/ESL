"""Finish a one-take render: deflicker, put on the clean studio plate, caption.
Usage: finish.py NAME   (reads out/sign_NAME_896_st8_s7_fast.mp4 + inputs/NAME.json)
Writes clean/onetake_NAME.mp4 (captioned) and clean/onetake_NAME_nocap.mp4.
Needs clean/plate.png from matte.py."""
import json, os, subprocess, sys
import cv2, numpy as np
from PIL import Image
from rembg import new_session, remove

os.chdir(os.path.expanduser(os.environ.get("SCAIL_HOME", "~/scail")))
name = sys.argv[1]
src = f"out/sign_{name}_896_st8_s7_fast.mp4"
spans = json.load(open(f"inputs/{name}.json"))
WORDS = {"00": "FATHER", "01": "DOCTOR", "02": "MOTHER", "03": "TEACHER", "04": "SISTER", "05": "INTELLIGENT",
         "06": "BROTHER", "07": "PATIENT", "08": "MORNING", "09a": "WAKE UP", "09b": "EARLY", "10": "WALK",
         "11": "SCHOOL", "12": "TOGETHER", "13": "SCHOOL", "14": "TEACHER", "15": "GIVE", "16a": "NEW",
         "16b": "BOOK", "17": "READ", "18": "CLASS", "19": "GOOD", "20": "RESULTS", "21": "EXCELLENT"}
plate = cv2.imread("clean/plate.png").astype(np.float32)
sess = new_session("birefnet-portrait")
SIG_XY, SIG_T, DS = 40, 4.0, 8


def frames():
    cap = cv2.VideoCapture(src)
    while True:
        ok, f = cap.read()
        if not ok:
            return
        yield f


# pass 1: low-frequency layer (kept small) and matte per frame
lows, alphas = [], []
for i, f in enumerate(frames()):
    h, w = f.shape[:2]
    lows.append(cv2.resize(cv2.GaussianBlur(f.astype(np.float32), (0, 0), SIG_XY), (w // DS, h // DS),
                           interpolation=cv2.INTER_AREA))
    m = remove(Image.fromarray(f[:, :, ::-1]), session=sess, only_mask=True, post_process_mask=False)
    alphas.append(np.asarray(m, np.uint8))
    if i % 100 == 0:
        print("pass1", i, flush=True)
n = len(lows)
low = np.stack(lows)
r = int(3 * SIG_T)
k = np.exp(-0.5 * (np.arange(-r, r + 1) / SIG_T) ** 2); k /= k.sum()
pad = np.concatenate([low[:1].repeat(r, 0), low, low[-1:].repeat(r, 0)])
delta = np.stack([np.tensordot(k, pad[i:i + 2 * r + 1], axes=1) for i in range(n)]) - low


def word(i):
    t = [s[0] for s in spans if s[1] <= i < s[2]]
    return WORDS.get(t[-1], "") if t else ""


def caption(f, wd):
    if not wd:
        return f
    font, sc, th = cv2.FONT_HERSHEY_DUPLEX, 1.3, 2
    (tw, tht), _ = cv2.getTextSize(wd, font, sc, th)
    x, y = (f.shape[1] - tw) // 2, f.shape[0] - 40
    ov = f.copy()
    cv2.rectangle(ov, (x - 14, y - tht - 14), (x + tw + 14, y + 14), (0, 0, 0), -1)
    f = cv2.addWeighted(ov, 0.55, f, 0.45, 0)
    cv2.putText(f, wd, (x, y), font, sc, (255, 255, 255), th, cv2.LINE_AA)
    return f


def writer(path):
    return subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                             "-s", f"{w}x{h}", "-r", "25", "-i", "-", "-c:v", "libx264", "-crf", "14",
                             "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)


wc, wn = writer(f"clean/onetake_{name}.mp4"), writer(f"clean/onetake_{name}_nocap.mp4")
for i, f in enumerate(frames()):
    f = f.astype(np.float32) + cv2.resize(delta[i], (w, h), interpolation=cv2.INTER_CUBIC)
    # 1-2-1 temporal smoothing of the matte so the cut-out edge does not shimmer
    a = (0.25 * alphas[max(i - 1, 0)] + 0.5 * alphas[i] + 0.25 * alphas[min(i + 1, n - 1)]) / 255
    a = a[..., None]
    out = np.clip(f * a + plate * (1 - a), 0, 255).astype(np.uint8)
    wn.stdin.write(out.tobytes())
    wc.stdin.write(caption(out, word(i)).tobytes())
for p in (wc, wn):
    p.stdin.close(); p.wait()
print("done", n, "frames", flush=True)
