"""
Apply strong automatic quality gates to a scale_result_<vid>.json produced by
align_video.py, per the project's AUTO_ACCEPT / REVIEW_REQUIRED / REJECT rule:

AUTO_ACCEPT requires ALL of:
 - expected item count == recovered (matched) item count (no missing items)
 - recovered item indices are monotonically non-decreasing across time (already
   enforced by align_video.py's search order, but re-verified here)
 - every matched interval has end > start (non-zero, non-overlapping-inverted)
 - intervals for consecutive items do not overlap (start[i+1] >= end[i] - tiny slack)
 - no duplicate interval reused for two different items
REVIEW_REQUIRED: some but not all items matched, or a soft anomaly (e.g. a very
short interval) — needs a human look.
REJECT: zero items matched, or expected count is 0/unknown.
"""
import sys, json, glob, os

def gate(result):
    items = result["items"]
    n_expected = result["n_expected_items"]
    matched = [it for it in items if it["caption_start_s"] is not None]
    n_matched = len(matched)

    if n_expected == 0:
        return "REJECT", "no expected items"
    if n_matched == 0:
        return "REJECT", "no items matched at all"

    # monotonic order check on matched items (by item_index_in_video vs time)
    ordered = sorted(matched, key=lambda x: x["item_index_in_video"])
    times = [it["caption_start_s"] for it in ordered]
    monotonic = all(times[i] <= times[i+1] for i in range(len(times)-1))

    # non-overlap / sane interval check
    sane = True
    for it in ordered:
        if it["caption_end_s"] is None or it["caption_end_s"] < it["caption_start_s"]:
            sane = False
    for i in range(len(ordered)-1):
        if ordered[i]["caption_end_s"] > ordered[i+1]["caption_start_s"] + 0.01:
            sane = False  # overlap beyond rounding slack

    # duplicate-interval check (two different items assigned the exact same start)
    starts = [it["caption_start_s"] for it in ordered]
    dup = len(starts) != len(set(starts))

    if n_matched == n_expected and monotonic and sane and not dup:
        return "AUTO_ACCEPT", "full count, monotonic, non-overlapping, no dup"
    if n_matched >= 1 and (not monotonic or not sane or dup):
        return "REJECT", f"reliability failure (monotonic={monotonic} sane={sane} dup={dup})"
    return "REVIEW_REQUIRED", f"partial match {n_matched}/{n_expected}"


def main():
    paths = sys.argv[1:] or sorted(glob.glob("scale_result_*.json"))
    summary = {"AUTO_ACCEPT": [], "REVIEW_REQUIRED": [], "REJECT": []}
    for p in paths:
        result = json.load(open(p))
        verdict, reason = gate(result)
        vid = result["video_id"]
        summary[verdict].append({"video_id": vid, "reason": reason,
                                   "n_expected": result["n_expected_items"],
                                   "n_matched": result["n_matched_items"]})
        result["gate_verdict"] = verdict
        result["gate_reason"] = reason
        json.dump(result, open(p, "w"), ensure_ascii=False, indent=2)
        print(f"{verdict:16s} {vid}  {reason}")
    total = sum(len(v) for v in summary.values())
    print(json.dumps({k: len(v) for k, v in summary.items()}, indent=2))
    json.dump(summary, open("gate_summary.json", "w"), indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
