import sys, json, easyocr
import align_video as av

VIDEO_IDS = sys.argv[1:]

def main():
    reader = easyocr.Reader(["en", "ar"], gpu=False)
    av.align.reader = reader
    summary = []
    for vid in VIDEO_IDS:
        try:
            items = av.load_items(vid)
            if not items:
                print(f"SKIP {vid}: no corpus items")
                continue
            video_path = av.download(vid)
            frames_dir = av.extract_frames(vid, video_path)
            ocr_results = av.run_ocr(vid, frames_dir, reader)
            assigned, intervals = av.align(vid, items, ocr_results)
            n_expected = len(items)
            n_matched = len(intervals)
            result = {
                "video_id": vid,
                "n_expected_items": n_expected,
                "n_matched_items": n_matched,
                "items": [{"item_index_in_video": it['item_index_in_video'],
                            "arabic_caption": it['arabic_caption'],
                            "english_meaning_from_video": it['english_meaning_from_video'],
                            "content_type": it['content_type'],
                            "caption_start_s": intervals.get(it['item_index_in_video'], [None, None])[0],
                            "caption_end_s": intervals.get(it['item_index_in_video'], [None, None])[1]}
                           for it in items],
            }
            out_path = f"scale_result_{vid}.json"
            json.dump(result, open(out_path, "w"), ensure_ascii=False, indent=2)
            print(f"OK {vid}: expected={n_expected} matched={n_matched}")
            summary.append((vid, n_expected, n_matched))
        except Exception as e:
            print(f"ERROR {vid}: {e}")
    print("SUMMARY", summary)

if __name__ == "__main__":
    main()
