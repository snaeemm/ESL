"""Join per-sign renders into the captioned lesson, with plain cuts or short crossfades.
Usage: assemble_lesson.py SRC_DIR OUT.mp4 [FADE_FRAMES]   (SRC_DIR holds <TAG>.mp4; default fade 0)"""
import subprocess, sys
import cv2, numpy as np

src, dst = sys.argv[1], sys.argv[2]
FADE = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SIGNS = [("00", "FATHER"), ("01", "DOCTOR"), ("02", "MOTHER"), ("03", "TEACHER"), ("04", "SISTER"),
         ("05", "INTELLIGENT"), ("06", "BROTHER"), ("07", "PATIENT"), ("08", "MORNING"), ("09a", "WAKE UP"),
         ("09b", "EARLY"), ("10", "WALK"), ("11", "SCHOOL"), ("12", "TOGETHER"), ("13", "SCHOOL"),
         ("14", "TEACHER"), ("15", "GIVE"), ("16a", "NEW"), ("16b", "BOOK"), ("17", "READ"), ("18", "CLASS"),
         ("19", "GOOD"), ("20", "RESULTS"), ("21", "EXCELLENT")]


def read(path, n_max=10 ** 6):
    cap, out = cv2.VideoCapture(path), []
    while len(out) < n_max:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(f, (896, 512)))
    return out


def caption(f, word):
    f = f.copy()
    font, sc, th = cv2.FONT_HERSHEY_DUPLEX, 1.3, 2
    (tw, tht), _ = cv2.getTextSize(word, font, sc, th)
    x, y = (f.shape[1] - tw) // 2, f.shape[0] - 40
    ov = f.copy()
    cv2.rectangle(ov, (x - 14, y - tht - 14), (x + tw + 14, y + 14), (0, 0, 0), -1)
    f = cv2.addWeighted(ov, 0.55, f, 0.45, 0)
    cv2.putText(f, word, (x, y), font, sc, (255, 255, 255), th, cv2.LINE_AA)
    return f


clips = [[caption(f, w) for f in read(f"{src}/{t}.mp4", 52 if t == "21" else 10 ** 6)] for t, w in SIGNS]
out = list(clips[0])
for c in clips[1:]:
    if FADE == 0:  # plain cut: out[-0:] would be the whole list
        out.extend(c)
        continue
    tail = out[-FADE:]
    del out[-FADE:]
    for i in range(FADE):
        a = (i + 1) / (FADE + 1)
        out.append(cv2.addWeighted(tail[i], 1 - a, c[i], a, 0))
    out.extend(c[FADE:])
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "896x512",
                      "-r", "25", "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", dst],
                     stdin=subprocess.PIPE)
for f in out:
    p.stdin.write(f.tobytes())
p.stdin.close(); p.wait()
print(len(out) / 25, "s")
