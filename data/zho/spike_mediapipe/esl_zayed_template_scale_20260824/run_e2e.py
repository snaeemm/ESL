import sys, os, json, traceback

ROOT = "."
sys.path.insert(0, ROOT)
from lib import pipeline_runner as pr

FIXTURES = {
    "family_school_en": "content/test_b_family_school.md",
    "family_school_ar": "content/test_c_family_school_ar.md",
    "emirati_d": "content/test_d_emirati.md",
    "cells": "content/grade6_science_ch3_cells.md",
    "photosynthesis": "content/photosynthesis_constructed.md",
    "general_vocab_daily_habits": "content/test_e_general_vocab_daily_habits.md",
    "general_vocab_shopping_gifts": "content/test_f_general_vocab_shopping_gifts.md",
}

def main():
    names = sys.argv[1:] or list(FIXTURES.keys())
    for name in names:
        src = os.path.join(ROOT, FIXTURES[name])
        out_dir = os.path.join(ROOT, "data/zho/spike_mediapipe/esl_zayed_template_scale_20260824/e2e_out", name)
        os.makedirs(out_dir, exist_ok=True)
        print(f"=== {name} ===")
        try:
            last = None
            for ev in pr.run(src, out_dir, skip_clip_prep=True, allow_review_render=True):
                last = ev
                print(" ", ev.get("stage"), ev.get("status"), ev.get("message", "")[:120])
        except Exception as e:
            print("  EXCEPTION:", e)
            traceback.print_exc()
        # summarize traceability if present
        trace_path = os.path.join(out_dir, "traceability.json")
        if os.path.exists(trace_path):
            trace = json.load(open(trace_path))
            counts = {}
            for seg in trace.get("segments", trace if isinstance(trace, list) else []):
                pass
            print("  traceability.json written:", trace_path)
        print()

if __name__ == "__main__":
    main()
