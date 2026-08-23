#!/usr/bin/env python3
"""
Upgrade data/zho/catalog.json to a bilingual catalog by crawling the same ZHO
search endpoint a second time with l=ar-AE and joining on the stable Sitecore
item Id (the same "id" field already used in the English-only catalog).

The Id is a Sitecore content-item GUID - it does not change with locale, so
it is a safe, exact join key (much stronger than matching on translated
text). This was verified manually before writing this script: fetching the
same offset with l=en vs l=ar-AE returns items with matching Id/Path but
different <h5 class="field-title"> text, e.g. "Amma" / "عم \\ عمه".

Video/thumb URLs are locale-agnostic (confirmed in the original English
crawl's coverage report), so we do not need them from the Arabic pass - we
only pull word_ar and category (Arabic category name is captured too, for
category_ar, though it isn't used by the resolver yet).

Arabic result count (1142) is one less than English (1143) - this script
does a FULL crawl of the ar-AE result set across all pages, not just page 0,
and reports any English id that has no Arabic counterpart rather than
silently guessing. It does not fabricate an Arabic label for anything it
can't find.

Output: rewrites data/zho/catalog.json in place, adding word_ar/category_ar
where found, plus a "schema_version": 2 marker record structure. word_en/
category/id/video fields are left untouched for backward compatibility.
Writes data/zho/catalog_bilingual_report.json with join diagnostics.
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

SEARCH_PARAMS = {
    "v": "{FF1E6744-6C43-40A7-835E-D75CE4092535}",
    "s": "{9D475605-DBA6-4E8A-BA9A-7949E0F32CF5}",
    "itemid": "{5596362A-FE9B-4ABC-844F-921767C0AE1F}",
    "sig": "mastercard",
    "l": "ar-AE",
}
PAGE_SIZE = 20

TITLE_RE = re.compile(r'field-title["\']?>(.*?)</h5>', re.S)


def fetch_page(offset: int) -> dict:
    params = dict(SEARCH_PARAMS)
    params["e"] = str(offset)
    url = f"{SEARCH_ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_title(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw or "").strip()


def parse_result_ar(item: dict) -> dict:
    html = item.get("Html") or ""
    title_m = TITLE_RE.search(html)
    path_parts = item["Path"].split("/")
    try:
        di = path_parts.index("Data")
        category_ar = path_parts[di + 2]
    except (ValueError, IndexError):
        category_ar = None
    return {
        "id": item["Id"],
        "word_ar": clean_title(title_m.group(1)) if title_m else None,
        "category_ar_path": category_ar,
    }


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(root, "data", "zho", "catalog.json")
    report_path = os.path.join(root, "data", "zho", "catalog_bilingual_report.json")

    with open(catalog_path, encoding="utf-8") as f:
        rows = json.load(f)
    en_ids = {r["id"] for r in rows}
    print(f"English catalog: {len(rows)} entries", file=sys.stderr)

    first = fetch_page(0)
    total = first["Count"]
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"Arabic locale reports {total} items, fetching {pages} pages...", file=sys.stderr)

    ar_by_id = {}
    for page_num in range(pages):
        offset = page_num * PAGE_SIZE
        data = first if offset == 0 else fetch_page(offset)
        for item in data["Results"]:
            row = parse_result_ar(item)
            ar_by_id[row["id"]] = row
        print(f"  offset {offset}: {len(data['Results'])} results, "
              f"{len(ar_by_id)} unique so far", file=sys.stderr)
        if offset > 0:
            time.sleep(0.15)

    matched, missing_ar, no_title = 0, [], []
    for r in rows:
        ar = ar_by_id.get(r["id"])
        if ar is None:
            missing_ar.append({"id": r["id"], "word_en": r["word_en"]})
            r["word_ar"] = None
            r["category_ar_path"] = None
        elif not ar["word_ar"]:
            no_title.append({"id": r["id"], "word_en": r["word_en"]})
            r["word_ar"] = None
            r["category_ar_path"] = ar["category_ar_path"]
        else:
            matched += 1
            r["word_ar"] = ar["word_ar"]
            r["category_ar_path"] = ar["category_ar_path"]

    ar_only_ids = set(ar_by_id) - en_ids
    for r in rows:
        r["schema_version"] = 2

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    report = {
        "english_total": len(rows),
        "arabic_locale_reported_count": total,
        "arabic_matched_by_id": matched,
        "missing_arabic_counterpart": missing_ar,
        "matched_id_but_empty_title": no_title,
        "arabic_ids_not_in_english_catalog": sorted(ar_only_ids),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Matched EN+AR by stable id: {matched}/{len(rows)}", file=sys.stderr)
    print(f"Missing Arabic counterpart entirely: {len(missing_ar)}", file=sys.stderr)
    print(f"Id matched but empty Arabic title: {len(no_title)}", file=sys.stderr)
    print(f"Arabic-locale ids with no English counterpart: {len(ar_only_ids)}", file=sys.stderr)
    print(f"Wrote {catalog_path} and {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
