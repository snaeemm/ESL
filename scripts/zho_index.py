#!/usr/bin/env python3
"""
Index the full ZHO (Zayed Higher Organization) UAE Sign Language Dictionary.

The public site (za.gov.ae) is a Sitecore SXA site. Word cards are not present
in the static HTML or in the plain JSON search endpoint - the JSON only
carries item paths. Passing the SXA rendering-view GUID ("v") to the same
search endpoint additionally returns server-rendered card HTML per item,
which contains the actual video URL (a direct, signed Vimeo progressive-
download MP4 link) and thumbnail image path.

Direct navigation to the per-item detail pages (/en/Data/Sign-Category-Items/...)
is blocked by an edge WAF rule that rejects any URL containing the path
segment "Data" - this affects ALL such URLs, not just ours (confirmed via
category-root and other item probes). This is a real blocker: it means the
per-item HTML pages cannot be scraped directly. The search API workaround
above avoids it entirely, so it does not block indexing/download, but it
should be flagged as a fragile dependency (see coverage report).

Output: data/zho/catalog.json - one row per dictionary entry with word,
category, video_url, thumb_url, vimeo_id, source item path/url.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://www.za.gov.ae"
SEARCH_ENDPOINT = f"{BASE}/en/sxa/search/results/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Discovered from the category listing page's SXA search-results component
# data-properties attribute.
SEARCH_PARAMS = {
    "v": "{FF1E6744-6C43-40A7-835E-D75CE4092535}",   # rendering view (needed for Html)
    "s": "{9D475605-DBA6-4E8A-BA9A-7949E0F32CF5}",   # search results datasource
    "itemid": "{5596362A-FE9B-4ABC-844F-921767C0AE1F}",
    "sig": "mastercard",
    "l": "en",
}
PAGE_SIZE = 20  # server-enforced; pageSize param is ignored

TITLE_RE = re.compile(r'field-title["\']?>(.*?)</h5>', re.S)
VIDEO_RE = re.compile(r'href="(https://player\.vimeo\.com[^"]+)"')
THUMB_RE = re.compile(r"data-thumb='([^']*)'")
VIMEO_ID_RE = re.compile(r"/external/(\d+)\.")


def fetch_page(offset: int) -> dict:
    # NOTE: the "page" query param is silently ignored by this endpoint -
    # every value returns the same first 20 results. The real pagination
    # parameter is "e" (a 0-indexed item offset), discovered by trial.
    params = dict(SEARCH_PARAMS)
    params["e"] = str(offset)
    url = f"{SEARCH_ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_title(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw or "").strip()
    return text


def parse_result(item: dict) -> dict:
    html = item.get("Html") or ""
    title_m = TITLE_RE.search(html)
    video_m = VIDEO_RE.search(html)
    thumb_m = THUMB_RE.search(html)

    path_parts = item["Path"].split("/")
    # .../Data/Sign Category Items/<Category>/<Slug>
    try:
        di = path_parts.index("Data")
        category = path_parts[di + 2]
    except (ValueError, IndexError):
        category = None

    video_url = video_m.group(1).replace("&amp;", "&") if video_m else None
    vimeo_id_m = VIMEO_ID_RE.search(video_url) if video_url else None

    return {
        "id": item["Id"],
        "word_en": clean_title(title_m.group(1)) if title_m else None,
        "category": category,
        "item_path": item["Path"],
        "item_url": item["Url"],
        "video_url": video_url,
        "vimeo_id": vimeo_id_m.group(1) if vimeo_id_m else None,
        "thumb_path": thumb_m.group(1) if thumb_m else None,
        "has_video": video_url is not None,
    }


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(root, "data/zho/catalog.json")

    first = fetch_page(0)
    total = first["Count"]
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"Total items reported: {total}, fetching {pages} pages...", file=sys.stderr)

    seen = {}
    for page_num in range(pages):
        offset = page_num * PAGE_SIZE
        data = first if offset == 0 else fetch_page(offset)
        for item in data["Results"]:
            row = parse_result(item)
            seen[row["id"]] = row
        print(f"  offset {offset}: {len(data['Results'])} results, "
              f"{len(seen)} unique so far", file=sys.stderr)
        time.sleep(0.15)  # be polite to a government server

    rows = list(seen.values())
    missing_video = [r for r in rows if not r["has_video"]]
    print(f"Done. {len(rows)} unique items indexed. "
          f"{len(missing_video)} with no parsed video URL.", file=sys.stderr)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
