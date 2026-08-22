# Benchmarks

Two independent evaluations, both run locally via Ollama on this project's four candidate models
(`qwen3:latest`, `hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M`, `jais-adaptive-q4:7b`, `qwen3.5-9b:q4`).
Rescued from a session-scoped scratchpad into this repo on 2026-08-19 — scripts and raw results below,
matching the numbers recorded in project memory (`project-moi-case-study`).

## `llm_grounding/` — the required benchmark (brief Section 4)

**What it tests:** given the real Episode 1 source text (`content/grade6_science_ch3_cells.md`, English),
can each model extract a structured JSON array of `{concept, key_terms, source_span}` that stays strictly
grounded in that source — i.e. does the "Understand" pipeline stage actually work. This is the LLM's *only*
job in the architecture (concept extraction from English source text); it does not touch Arabic, dialect, or
sign language at all — those are handled downstream by deterministic glossary lookup, by design (brief Section 1).

**How to rerun:** `run_ch3_benchmark.py` — needs `requests`, `scikit-learn`, `rouge-score`, `nltk` (a fresh
`uv venv` + `uv pip install requests scikit-learn rouge-score nltk` is enough) and a running local Ollama
server with the four models pulled. Prompts each model for the JSON array (temperature=0, `think: false` for
reasoning-capable models, `repeat_penalty: 1.3`), parses the response, and scores TF-IDF cosine similarity,
ROUGE-1/L, Jaccard token overlap, and BLEU against the source text, plus a bonus **source-span verbatim-match
rate** (does the model's claimed quote actually exist word-for-word in the source — the most direct proxy for
the case study's core traceability requirement).

`retry_jais.py` and `retry_jais_chunked.py` are follow-up debugging scripts specifically for
`jais-adaptive-q4:7b`, which failed to produce valid JSON in the main run — see Results below.

**Final numbers** (`results/ch3_benchmark_results_v3_FINAL.log` — the v1/v2 logs are earlier attempts kept
for the debugging trail, not the final numbers):

| Model | Cosine | ROUGE-1 | ROUGE-L | Jaccard | BLEU | Source-span match | Concepts | Valid JSON? |
|---|---|---|---|---|---|---|---|---|
| **Falcon-H1-7B** (winner) | **0.908** | **0.755** | **0.734** | **0.664** | **0.597** | 85.7% | 7 | ✅ |
| Qwen3.5-9B | 0.808 | 0.574 | 0.522 | 0.484 | 0.310 | **88.9%** | 9 | ✅ |
| Qwen3-8B | 0.793 | 0.576 | 0.503 | 0.470 | 0.315 | 60.0% | 10 | ✅ |
| jais-adaptive-7B | 0.510 | 0.120 | 0.094 | 0.116 | 0.000 | 0% | 0 | ❌ |

**Winner per the brief's own rule** ("the model with the best grounding-faithfulness score is used in the
live demo"): **Falcon-H1-7B-Instruct** — wins every metric the brief explicitly names, narrowly loses only
the bonus source-span metric to Qwen3.5-9B.

**jais-adaptive note:** reliably fails to produce valid JSON on the full document in one pass (raw outputs in
`results/ch3_extraction_jais-adaptive-q4_7b.json` and `results/jais_chunked_results.json`). Debugged
extensively (7 distinct mitigation attempts across `retry_jais.py`/`retry_jais_chunked.py`: few-shot prompting,
simplified schema, chunking into one-section-at-a-time calls, a parser fix for a specific literal-`\n`
formatting artifact, raised token budgets, chain-of-thought prompting). Conclusion: with per-section chunking
it handles 3 of 4 sections correctly, but the densest section (covering all 4 organelles in one paragraph)
fails consistently regardless of strategy — a genuine content-complexity ceiling, not a config bug. Full
narrative in project memory; don't oversimplify to either "jais-adaptive can't do it" or "works fine with a
little post-processing" — both are inaccurate.

**Also worth knowing:** two apparent "failures" in earlier runs (`v1`/`v2` logs) were actually misconfiguration,
not incapability — Qwen3.5-9B is reasoning-tuned and burned its whole token budget on internal deliberation
before `think: false` was added; that's why v3 is the correct/final run.

## `alyah/` — supplementary Emirati-dialect benchmark

**What it tests:** NOT part of the required brief deliverable. A separate question — how well do these same
four models understand actual Emirati/Khaliji Arabic dialect, using TII's own public "Alyah" benchmark
(`alyah_test.parquet`, 1,173 multiple-choice questions across 7 categories: language/dialect, figurative
meaning, etiquette, religious sensitivity, heritage, greetings, poetry — source:
[huggingface.co/datasets/tiiuae/alyah-emirati-benchmark](https://huggingface.co/datasets/tiiuae/alyah-emirati-benchmark)).
Useful supporting evidence for the "Model Selection" narrative (and for the production-path argument — see
project memory), since the pipeline's actual LLM stage never touches Arabic/dialect content directly.

**How to rerun:** `run_alyah_eval.py` — same deps as above. Same prompt template per model (Arabic instruction
to answer with only the option number), temperature=0, `think: false`, regex-parsed 1-4 answer, scored against
`correct_answer`. Checkpointed incrementally to `results/alyah_checkpoint.jsonl` — safe to kill and rerun,
already-scored question/model pairs are skipped automatically.

**Final numbers** (`results/alyah_eval_FINAL.log`):

| Model | Accuracy | Parse rate |
|---|---|---|
| **Falcon-H1-7B** (winner) | **64.88%** | 100% |
| Qwen3-8B | 64.11% | 100% |
| jais-adaptive-7B | 51.41% | 99.5% |
| Qwen3.5-9B | 26.00% | 100% |

Falcon-H1 and Qwen3 are essentially tied (0.77-point gap on 1,173 questions — not meaningful). Notable finding:
Qwen3.5-9B collapses here despite winning the Ch.3 benchmark above — concrete evidence that "newer generation"
doesn't mean "better at everything," and why each pipeline stage/task should be benchmarked independently
rather than assuming general capability transfers.

**Context from TII's own published leaderboard** (same benchmark, different models, see blog link above): a
*closed, not-publicly-available* Arabic-specialized model (`falcon-h1-arabic-7b-instruct`) scored 82.18% — well
above anything we could actually deploy locally. Their general-purpose reference points (Gemma-3-27B,
Qwen2.5-72B) scored ~74.6%, above our 7B Falcon-H1's 64.88%, which is reasonable given the size difference.
Worth citing this honestly as a real production-path argument (formal MoE↔TII partnership, or LoRA fine-tuning
Falcon-H1 on verified curriculum data) rather than overselling the current prototype's dialect capability.

**`qwen3:latest` gotcha (already fixed, note for future rerunners):** an earlier attempt scored qwen3 at a flat
0.0% accuracy *and* 0.0% parse rate — that exact-zero-on-both pattern is a tell for a config bug, not a real
result. Root cause: qwen3 is also reasoning-capable, and without `think: false` it got stuck opening a
`<think>` block and never reached an answer digit within the 5-token budget. `run_alyah_eval.py` as committed
here already has the fix; if you ever adapt this script for a new reasoning-capable model, keep `think: false`
in the request or this will silently recur.
