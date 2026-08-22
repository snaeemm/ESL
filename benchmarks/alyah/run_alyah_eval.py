import pandas as pd
import requests
import re
import sys
import json
import time
import os

DATA_PATH = "/private/tmp/claude-501/-Users-shaz-MOI-Arabic-Sign-Language/a3e00aef-4d03-4ba3-b410-a08b4dd3124e/scratchpad/alyah_test.parquet"
CHECKPOINT_PATH = "/private/tmp/claude-501/-Users-shaz-MOI-Arabic-Sign-Language/a3e00aef-4d03-4ba3-b410-a08b4dd3124e/scratchpad/alyah_checkpoint.jsonl"

df = pd.read_parquet(DATA_PATH)
print(f"Total questions: {len(df)}", flush=True)
print(f"Categories: {list(df['category'].unique())}", flush=True)

MODELS = [
    "qwen3:latest",
    "hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M",
    "jais-adaptive-q4:7b",
    "qwen3.5-9b:q4",
]

done = set()
if os.path.exists(CHECKPOINT_PATH):
    with open(CHECKPOINT_PATH) as f:
        for line in f:
            rec = json.loads(line)
            done.add((rec["model"], rec["idx"]))
    print(f"Resuming: {len(done)} question-model pairs already done", flush=True)

def ask(model, query, opts):
    prompt = (
        "أجب فقط برقم الخيار الصحيح (1 أو 2 أو 3 أو 4)، بدون أي شرح.\n\n"
        f"السؤال: {query}\n"
        f"1) {opts[0]}\n2) {opts[1]}\n3) {opts[2]}\n4) {opts[3]}\n\nالإجابة:"
    )
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "think": False, "options": {"num_predict": 5, "temperature": 0.0}},
        timeout=120,
    )
    r.raise_for_status()
    resp = r.json()["response"]
    m = re.search(r"[1-4]", resp)
    return int(m.group()) if m else None

ckpt_file = open(CHECKPOINT_PATH, "a")

for model in MODELS:
    start = time.time()
    correct = sum(1 for (m, i) in done if m == model)  # placeholder, recomputed below properly
    n_done_for_model = 0
    correct = 0
    answered = 0
    for idx, row in df.iterrows():
        if (model, idx) in done:
            continue
        try:
            pred = ask(model, row["query"], opts=[row["option_1"], row["option_2"], row["option_3"], row["option_4"]])
        except Exception as e:
            pred = None
        rec = {"model": model, "idx": int(idx), "category": row["category"], "pred": pred, "correct_answer": int(row["correct_answer"])}
        ckpt_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ckpt_file.flush()
        n_done_for_model += 1
        if n_done_for_model % 50 == 0:
            elapsed = time.time() - start
            rate = n_done_for_model / elapsed
            remaining = (len(df) - n_done_for_model) / rate if rate > 0 else 0
            print(f"[{model}] {n_done_for_model}/{len(df)} done, {elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining", flush=True)

ckpt_file.close()

# Final scoring from checkpoint file (covers this run + any resumed prior data)
all_recs = []
with open(CHECKPOINT_PATH) as f:
    for line in f:
        all_recs.append(json.loads(line))

results = {}
for model in MODELS:
    recs = [r for r in all_recs if r["model"] == model]
    correct = sum(1 for r in recs if r["pred"] == r["correct_answer"])
    answered = sum(1 for r in recs if r["pred"] is not None)
    total = len(recs)
    acc = correct / total * 100 if total else 0
    parse_rate = answered / total * 100 if total else 0
    results[model] = {"accuracy": round(acc, 2), "correct": correct, "total": total, "parse_rate": round(parse_rate, 2)}

    # per-category breakdown
    cats = {}
    for r in recs:
        c = r["category"]
        cats.setdefault(c, {"correct": 0, "total": 0})
        cats[c]["total"] += 1
        if r["pred"] == r["correct_answer"]:
            cats[c]["correct"] += 1
    results[model]["by_category"] = {k: f"{v['correct']}/{v['total']} ({v['correct']/v['total']*100:.0f}%)" for k, v in cats.items()}

print("\n=== FINAL RESULTS ===", flush=True)
print(json.dumps(results, indent=2, ensure_ascii=False), flush=True)
