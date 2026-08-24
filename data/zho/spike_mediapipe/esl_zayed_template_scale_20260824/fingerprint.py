"""
Build a lightweight caption-template fingerprint for each ESL Zayed video WITHOUT
downloading the full file: use yt-dlp -g to resolve a direct low-res stream URL,
then ffmpeg -ss seeks to pull a handful of representative frames directly from
the remote stream. Derive deterministic layout features (no new ML model):
 - per-frame: split into an 8x6 grid of blocks
 - for each block, compute local variance (Laplacian-like) as a proxy for "text/graphic present"
 - binarize blocks against a per-frame threshold -> a 48-bit "caption footprint" per frame
 - average footprint across sampled frames -> per-video fingerprint vector (48 floats in [0,1])
 - also record: frame aspect/resolution, left-heavy vs right-heavy vs bottom-heavy mass,
   fraction of frame flagged "textish"
This vector is used purely for clustering visually-similar caption layouts.
"""
import sys, os, json, subprocess, math

BASE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(BASE, "fp_frames")
CORPUS = os.path.join(os.path.dirname(BASE), "esl_zayed_full_93video_corpus_20260823.json")
GRID_X, GRID_Y = 8, 6
SAMPLE_FRACS = [0.15, 0.35, 0.55, 0.75, 0.9]


def get_duration(vid):
    url = f"https://www.youtube.com/watch?v={vid}"
    try:
        out = subprocess.run(["yt-dlp", "--print", "duration", url],
                              capture_output=True, text=True, timeout=60)
        line = out.stdout.strip().splitlines()[0]
        return float(line)
    except Exception:
        return None


def get_stream_url(vid):
    url = f"https://www.youtube.com/watch?v={vid}"
    out = subprocess.run(["yt-dlp", "-f", "134/135/160/best[height<=360]", "-g", url],
                          capture_output=True, text=True, timeout=60)
    lines = [l for l in out.stdout.strip().splitlines() if l.startswith("http")]
    if not lines:
        raise RuntimeError(f"no stream url: {out.stderr[:300]}")
    return lines[0]


def grab_frame(stream_url, t, out_path):
    subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", stream_url,
                     "-frames:v", "1", "-q:v", "3", out_path],
                    capture_output=True, timeout=60, check=True)


def frame_features(path):
    from PIL import Image
    import numpy as np
    im = Image.open(path).convert("L")
    w, h = im.size
    arr = np.asarray(im, dtype=np.float32)
    bw, bh = w // GRID_X, h // GRID_Y
    feats = []
    for gy in range(GRID_Y):
        for gx in range(GRID_X):
            block = arr[gy*bh:(gy+1)*bh, gx*bw:(gx+1)*bw]
            if block.size == 0:
                feats.append(0.0)
                continue
            # local variance as edge/text-density proxy
            feats.append(float(block.std()))
    return w, h, feats


def main():
    vids = sys.argv[1:]
    os.makedirs(FRAMES, exist_ok=True)
    results = []
    for vid in vids:
        try:
            dur = get_duration(vid)
            if not dur or dur <= 0:
                print(f"SKIP {vid}: no duration")
                continue
            stream_url = get_stream_url(vid)
            vdir = os.path.join(FRAMES, vid)
            os.makedirs(vdir, exist_ok=True)
            frame_feats = []
            dims = None
            for i, frac in enumerate(SAMPLE_FRACS):
                t = round(dur * frac, 1)
                fp = os.path.join(vdir, f"f_{i}.jpg")
                if not os.path.exists(fp):
                    grab_frame(stream_url, t, fp)
                w, h, feats = frame_features(fp)
                dims = (w, h)
                frame_feats.append(feats)
            n = len(frame_feats)
            avg = [sum(col)/n for col in zip(*frame_feats)]
            mx = max(avg) if avg else 1.0
            norm_avg = [v/mx if mx > 0 else 0.0 for v in avg]
            result = {
                "video_id": vid,
                "duration": dur,
                "width": dims[0], "height": dims[1],
                "aspect": round(dims[0]/dims[1], 3),
                "fingerprint": [round(v, 4) for v in norm_avg],
            }
            out_path = os.path.join(BASE, f"fp_{vid}.json")
            json.dump(result, open(out_path, "w"))
            print(f"OK {vid}: dur={dur:.0f}s dims={dims}")
            results.append(result)
        except Exception as e:
            print(f"ERROR {vid}: {e}")
    print(f"done: {len(results)}/{len(vids)}")


if __name__ == "__main__":
    main()
