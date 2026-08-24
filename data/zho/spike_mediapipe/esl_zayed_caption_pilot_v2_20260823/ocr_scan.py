import sys, os, glob, json
import easyocr
from PIL import Image

# crop regions as fractions (x0,y0,x1,y1) of full frame, per video (identified by visual inspection)
REGIONS = {
    "ARH8U8S-RfI": (0.50, 0.05, 1.00, 0.45),   # right_box, word template, 360p 16:9
    "Ctz__kub2SE": (0.50, 0.10, 1.00, 0.45),   # right_box, word template, letterboxed 4:3-in-16:9
    "2l1WqXUZfC8": (0.20, 0.72, 0.80, 1.00),   # bottom_center_big letter template
}

def crop_frame(path, region):
    im = Image.open(path)
    w, h = im.size
    x0, y0, x1, y1 = region
    box = (int(x0*w), int(y0*h), int(x1*w), int(y1*h))
    return im.crop(box)

def main():
    vid = sys.argv[1]
    frames_dir = f"ocr_frames/{vid}"
    out_path = f"ocr_raw_{vid}.json"
    langs = ["en", "ar"]
    reader = easyocr.Reader(langs, gpu=False)
    region = REGIONS[vid]
    files = sorted(glob.glob(f"{frames_dir}/f_*.png"))
    results = []
    for i, f in enumerate(files):
        t = i * 0.5
        crop = crop_frame(f, region)
        crop_path = f"{frames_dir}/crop_{i:04d}.png"
        crop.save(crop_path)
        try:
            res = reader.readtext(crop_path, detail=0, paragraph=True)
        except Exception as e:
            res = [f"ERROR:{e}"]
        text = " | ".join(res)
        results.append({"t": round(t,1), "frame": os.path.basename(f), "text": text})
        print(f"{t:5.1f}s  {text}")
    json.dump(results, open(out_path, "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
