"""
Rebuild data/zho/esl_zayed_supplementary_catalog.json by merging:
 - the existing 66-record catalog (kept as-is, never removed)
 - new AUTO_ACCEPT WORD-content_type items from this session's scale_result_*.json
   files (in esl_zayed_caption_pilot_v2_20260823/), matched against gate_summary.json

Only WORD content_type items from AUTO_ACCEPT videos are added (PHRASE/SENTENCE/
DIALOGUE/NUMBER/LETTER are preserved separately in the timestamped corpus but are
NOT added to the WORD-only supplementary resolver catalog per production
authorization rules). Dedupes by (youtube_video_id, item_index_in_video).
"""
import json, os, glob

ROOT = "/Users/shaz/MOI-Arabic-Sign-Language/.claude/worktrees/agent-a3731017e37e9bf81"
CATALOG_PATH = os.path.join(ROOT, "data/zho/esl_zayed_supplementary_catalog.json")
RESULTS_DIR = os.path.join(ROOT, "data/zho/spike_mediapipe/esl_zayed_caption_pilot_v2_20260823")


def main():
    catalog = json.load(open(CATALOG_PATH))
    # dedupe on (video, normalized arabic text) rather than start_s: a video
    # already covered by an earlier manual/pilot pass may have the SAME item
    # recovered again by this session's automated alignment at a slightly
    # different timestamp -- text identity is the correct dedupe key, not time.
    existing_pairs = {(r["youtube_video_id"], r["arabic_text"].strip()) for r in catalog}

    next_num = max(int(r["supplementary_id"].split("_")[-1]) for r in catalog) + 1

    added = []
    result_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "scale_result_*.json")))
    for f in result_files:
        d = json.load(open(f))
        if d.get("gate_verdict") != "AUTO_ACCEPT":
            continue
        vid = d["video_id"]
        for it in d["items"]:
            if it["content_type"] != "WORD":
                continue
            if it["caption_start_s"] is None:
                continue
            key = (vid, it["arabic_caption"].strip())
            if key in existing_pairs:
                continue
            rec = {
                "supplementary_id": f"ESL_ZAYED_{next_num:04d}",
                "source": "ESL_ZAYED",
                "source_authority": "OBSERVED_EMIRATI_EDUCATIONAL_SOURCE",
                "arabic_text": it["arabic_caption"],
                "english_meaning": it["english_meaning_from_video"],
                "youtube_video_id": vid,
                "source_url": f"https://www.youtube.com/watch?v={vid}",
                "segment_start_s": it["caption_start_s"],
                "segment_end_s": it["caption_end_s"],
                "content_type": "WORD",
                "confidence": "HIGH",
                "matched_zho_ids": [],
                "notes": "template-cluster scale-up, OCR caption-identity alignment, AUTO_ACCEPT gate",
                "signer_note": "ESL Zayed teaching-card template",
                "verification_status": "SUPPLEMENTARY_UNVERIFIED",
            }
            catalog.append(rec)
            existing_pairs.add(key)
            added.append(rec)
            next_num += 1

    json.dump(catalog, open(CATALOG_PATH, "w"), ensure_ascii=False, indent=2)
    print(f"catalog size now: {len(catalog)} (+{len(added)} new)")
    for r in added:
        print(" +", r["supplementary_id"], r["youtube_video_id"], r["arabic_text"], "/", r["english_meaning"])


if __name__ == "__main__":
    main()
