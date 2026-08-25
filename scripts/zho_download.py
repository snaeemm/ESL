#!/usr/bin/env python3
"""
Download ZHO clips needed for Episode 1: the full Alphabets set (for
fingerspelling fallback) plus any direct matches for the episode term list.

Reads data/zho/catalog.json (produced by zho_index.py).
Writes clips to data/zho/clips/<category>/<slug>_<id8>.mp4
Writes thumbnails to data/zho/thumbs/<category>/<slug>_<id8>.jpg
Writes data/zho/download_manifest.json summarizing term match status.
"""
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = f"{ROOT}/data/zho/catalog.json"
CLIPS_DIR = f"{ROOT}/data/zho/clips"
THUMBS_DIR = f"{ROOT}/data/zho/thumbs"
MANIFEST = f"{ROOT}/data/zho/download_manifest.json"
THUMB_BASE = "https://www.za.gov.ae"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

EPISODE_TERMS = ("cell, membrane, nucleus, mitochondria, cytoplasm, organelle, "
                  "function, protect, energy, wall, plant, animal, structure, "
                  "small, inside, contain, produce, living, organism, body, "
                  "part, example, difference, compare").split(", ")


def slugify(word: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", word.strip()).strip("-").lower()
    return s or "unnamed"


def download(url: str, dest: str) -> bool:
    import os
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"  FAILED: {url} -> {e}", file=sys.stderr)
        return False


def main():
    import os
    rows = json.load(open(CATALOG, encoding="utf-8"))
    by_word = {}
    for r in rows:
        by_word.setdefault(r["word_en"].strip().lower(), []).append(r)

    # 1. Match episode terms (exact, case-insensitive only - see coverage
    #    report for why fuzzy substring matching was rejected as unreliable).
    term_matches = {}
    for t in EPISODE_TERMS:
        matches = by_word.get(t.lower(), [])
        term_matches[t] = matches

    # 2. Full Alphabets set.
    alphabet_rows = [r for r in rows if r["category"] == "Alphabets"]

    to_download = list(alphabet_rows)
    for matches in term_matches.values():
        to_download.extend(matches)

    print(f"Alphabet entries: {len(alphabet_rows)}", file=sys.stderr)
    print(f"Direct term matches: {sum(len(m) for m in term_matches.values())} "
          f"across {sum(1 for m in term_matches.values() if m)}/{len(EPISODE_TERMS)} terms",
          file=sys.stderr)
    print(f"Total clips to download: {len(to_download)}", file=sys.stderr)

    manifest_entries = []
    for i, row in enumerate(to_download, 1):
        cat_dir = os.path.join(CLIPS_DIR, row["category"])
        thumb_dir = os.path.join(THUMBS_DIR, row["category"])
        os.makedirs(cat_dir, exist_ok=True)
        os.makedirs(thumb_dir, exist_ok=True)

        slug = slugify(row["word_en"])
        id8 = row["id"][:8]
        clip_path = os.path.join(cat_dir, f"{slug}_{id8}.mp4")
        thumb_path = os.path.join(thumb_dir, f"{slug}_{id8}.jpg")

        ok_video = download(row["video_url"], clip_path) if row["video_url"] else False
        ok_thumb = False
        if row["thumb_path"]:
            thumb_url = THUMB_BASE + row["thumb_path"] + ".jpg"
            ok_thumb = download(thumb_url, thumb_path)

        manifest_entries.append({
            **row,
            "clip_path": clip_path if ok_video else None,
            "thumb_path_local": thumb_path if ok_thumb else None,
        })
        print(f"  [{i}/{len(to_download)}] {row['category']}/{row['word_en']}: "
              f"video={'ok' if ok_video else 'FAIL'} thumb={'ok' if ok_thumb else 'FAIL'}",
              file=sys.stderr)
        time.sleep(0.1)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({
            "episode_terms": EPISODE_TERMS,
            "term_matches": {t: [m["id"] for m in ms] for t, ms in term_matches.items()},
            "alphabet_ids": [r["id"] for r in alphabet_rows],
            "downloaded": manifest_entries,
        }, f, ensure_ascii=False, indent=2)
    print(f"Wrote {MANIFEST}", file=sys.stderr)


if __name__ == "__main__":
    main()
