import sys, os, json, glob
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(BASE, "fp_frames")
OUT = os.path.join(BASE, "contact_sheets")

def main():
    label = sys.argv[1]
    vids = sys.argv[2:]
    os.makedirs(OUT, exist_ok=True)
    thumb_w, thumb_h = 220, 124
    cols = 5
    rows = (len(vids) + cols - 1) // cols
    sheet = Image.new("RGB", (cols*thumb_w, rows*(thumb_h+18)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, vid in enumerate(vids):
        # use the middle sample frame (index 2 of 5)
        candidates = sorted(glob.glob(os.path.join(FRAMES, vid, "f_2.jpg")))
        if not candidates:
            candidates = sorted(glob.glob(os.path.join(FRAMES, vid, "f_*.jpg")))
        if not candidates:
            continue
        im = Image.open(candidates[0]).convert("RGB").resize((thumb_w, thumb_h))
        r, c = divmod(i, cols)
        x, y = c*thumb_w, r*(thumb_h+18)
        sheet.paste(im, (x, y))
        draw.text((x+2, y+thumb_h+2), vid, fill="black")
    out_path = os.path.join(OUT, f"{label}.jpg")
    sheet.save(out_path, quality=85)
    print(out_path)

if __name__ == "__main__":
    main()
