"""
Constrained OCR-based caption-identity alignment for one ESL Zayed video.
Given the known ordered labels (from the corpus JSON), sample frames sparsely,
OCR-crop the right_box caption region, and match against the current expected
label to recover per-item start/end boundaries.
"""
import sys, os, json, subprocess, glob, re
import easyocr
from PIL import Image

CORPUS = "/Users/shaz/MOI-Arabic-Sign-Language/.claude/worktrees/agent-a3731017e37e9bf81/data/zho/spike_mediapipe/esl_zayed_full_93video_corpus_20260823.json"
BASE = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE, "videos")
FRAMES_ROOT = os.path.join(BASE, "scale_frames")
STEP = 0.5  # seconds between samples

def norm(s):
    s = s.lower()
    s = re.sub(r'[^a-z؀-ۿ]', '', s)
    return s

def load_items(vid):
    data = json.load(open(CORPUS))
    items = [d for d in data if d['youtube_video_id'] == vid]
    items.sort(key=lambda x: x['item_index_in_video'])
    return items

def download(vid):
    out = os.path.join(VIDEOS_DIR, f"{vid}.mp4")
    if os.path.exists(out):
        return out
    subprocess.run(["yt-dlp", "-f", "135+140/134+139/best", "-o", out,
                     f"https://www.youtube.com/watch?v={vid}"], check=True,
                    capture_output=True)
    return out

def extract_frames(vid, video_path):
    d = os.path.join(FRAMES_ROOT, vid)
    os.makedirs(d, exist_ok=True)
    if glob.glob(f"{d}/f_*.png"):
        return d
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vf", f"fps={1/STEP}",
                     f"{d}/f_%04d.png"], check=True, capture_output=True)
    return d

def region_for(video_path):
    # right_box template default; works for both 16:9 and letterboxed-4:3-in-16:9
    return (0.20, 0.65, 0.80, 1.00)

def run_ocr(vid, frames_dir, reader):
    region = region_for(frames_dir)
    files = sorted(glob.glob(f"{frames_dir}/f_*.png"))
    out = []
    for i, f in enumerate(files):
        t = round(i * STEP, 1)
        im = Image.open(f)
        w, h = im.size
        x0, y0, x1, y1 = region
        crop = im.crop((int(x0*w), int(y0*h), int(x1*w), int(y1*h)))
        cpath = f + ".crop.png"
        crop.save(cpath)
        try:
            res = reader.readtext(cpath, detail=0, paragraph=True)
        except Exception as e:
            res = []
        text = " | ".join(res)
        out.append({"t": t, "text": text})
    return out

def align(vid, items, ocr_results):
    labels = [(it['item_index_in_video'], norm(it['english_meaning_from_video']), norm(it['arabic_caption'])) for it in items]
    # for each ocr sample, find best matching label index (must be in non-decreasing order)
    assigned = []
    cur_idx = 0
    for samp in ocr_results:
        text_norm = norm(samp['text'])
        match_idx = None
        # try current and next label first (monotonic expectation), then any forward
        search_order = list(range(cur_idx, len(labels)))
        for li in search_order:
            _, en, ar = labels[li]
            if en and en in text_norm:
                match_idx = li
                break
            if ar and ar in text_norm:
                match_idx = li
                break
        if match_idx is not None:
            cur_idx = match_idx
        assigned.append({"t": samp['t'], "text": samp['text'], "matched_item_index": match_idx})
    # derive intervals: for each item index, min/max t where matched
    intervals = {}
    for a in assigned:
        if a["matched_item_index"] is not None:
            idx = a["matched_item_index"]
            if idx not in intervals:
                intervals[idx] = [a["t"], a["t"]]
            else:
                intervals[idx][1] = a["t"]
    return assigned, intervals

def main():
    vid = sys.argv[1]
    items = load_items(vid)
    if not items:
        print(json.dumps({"video_id": vid, "error": "no corpus items"}))
        return
    video_path = download(vid)
    frames_dir = extract_frames(vid, video_path)
    reader = align.reader if hasattr(align, "reader") else easyocr.Reader(["en", "ar"], gpu=False)
    align.reader = reader
    ocr_results = run_ocr(vid, frames_dir, reader)
    assigned, intervals = align(vid, items, ocr_results)
    n_expected = len(items)
    n_matched = len(intervals)
    result = {
        "video_id": vid,
        "n_expected_items": n_expected,
        "n_matched_items": n_matched,
        "intervals": {str(k): v for k, v in intervals.items()},
        "items": [{"item_index_in_video": it['item_index_in_video'],
                    "arabic_caption": it['arabic_caption'],
                    "english_meaning_from_video": it['english_meaning_from_video'],
                    "content_type": it['content_type'],
                    "caption_start_s": intervals.get(it['item_index_in_video'], [None, None])[0],
                    "caption_end_s": intervals.get(it['item_index_in_video'], [None, None])[1]}
                   for it in items],
    }
    out_path = os.path.join(BASE, f"scale_result_{vid}.json")
    json.dump(result, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(json.dumps({"video_id": vid, "n_expected_items": n_expected, "n_matched_items": n_matched}, ensure_ascii=False))

if __name__ == "__main__":
    main()
