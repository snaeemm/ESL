#!/usr/bin/env python3
"""Benchmark: does a local multilingual embedding model recover
legitimately more ZHO catalog matches than plain lexical/token-overlap
retrieval, on OUR bilingual catalog - measured, not assumed.

Evaluation set: 30 hand-curated (query, expected_word_en) pairs below.
Every expected_word_en is a REAL catalog.json entry (verified present,
printed and checked against data/zho/catalog.json before being hand-
picked for this file - see chat/session notes). Every query is a genuine
paraphrase/synonym/translation that DELIBERATELY does NOT equal the
catalog's own word_en/word_ar string, so this measures semantic
recovery, not restating something exact/morphology matching would
already catch. Half the queries are in English, half in Arabic
(including cases where the catalog's own official word_ar is an unusual
compound, e.g. Father -> "باب الأسرة", to specifically test whether the
retriever finds it via a query using the ordinary Arabic word "أب").

Reports Recall@1 and Recall@5 for:
  - lexical  (lib/vocab_retrieval.py token-overlap retrieval)
  - nomic    (Ollama nomic-embed-text, lib/vocab_embedding.py)
  - e5-small (intfloat/multilingual-e5-small, lib/vocab_embedding_st.py)
  - minilm   (paraphrase-multilingual-MiniLM-L12-v2, lib/vocab_embedding_st.py)

Run: uv run --extra vocab-embedding-experiment python scripts/vocab_embedding_benchmark.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BENCHMARK = [
    ("unhappy", "Sad"),
    ("warm", "Hot"),
    ("physician", "Doctor"),
    ("educational institution", "School"),
    ("novel", "Book"),
    ("instructor", "Teacher"),
    ("afraid", "Scared"),
    ("relatives", "Family"),
    ("dad", "Father"),
    ("mom", "Mother"),
    ("sunshine", "Sun"),
    ("rainfall", "Rain"),
    ("cold season", "Winter"),
    ("hot season", "Summer"),
    ("quick", "Fast"),
    ("sluggish", "Slow"),
    ("ancient", "Old"),
    ("brand new", "New"),
    ("stroll", "Walk"),
    ("pretty", "Beautiful"),
    ("hideous", "Ugly"),
    ("حزن", "Sad"),
    ("طبيبة", "Doctor"),
    ("معلمة", "Teacher"),
    ("أب", "Father"),
    ("أم", "Mother"),
    ("شمس مشرقة", "Sun"),
    ("أمطار", "Rain"),
    ("سريع جدا", "Fast"),
    ("جميلة", "Beautiful"),
]


def recall_at_k(retrieve_fn, k):
    hits_1, hits_k, total = 0, 0, 0
    misleading = []
    for query, expected in BENCHMARK:
        total += 1
        candidates = retrieve_fn(query, k)
        words = [c.get("word_en") for c in candidates]
        if words and words[0] == expected:
            hits_1 += 1
        if expected in words:
            hits_k += 1
        else:
            misleading.append((query, expected, words))
    return {
        "recall@1": round(hits_1 / total, 3),
        f"recall@{k}": round(hits_k / total, 3),
        "misses": misleading,
    }


def bench_lexical():
    from lib.vocab_retrieval import get_index
    idx = get_index()
    return lambda q, k: idx.retrieve_candidates(q, top_n=k)


def bench_nomic():
    from lib.vocab_embedding import get_embedding_index
    idx = get_embedding_index()
    return lambda q, k: idx.retrieve_candidates(q, top_n=k, min_similarity=0.0)


def bench_st(model_key):
    from lib.vocab_embedding_st import get_index
    idx = get_index(model_key)
    return lambda q, k: idx.retrieve_candidates(q, top_n=k)


def main():
    results = {}
    for name, builder in [("lexical", bench_lexical), ("nomic", bench_nomic),
                           ("e5-small", lambda: bench_st("e5-small")),
                           ("minilm", lambda: bench_st("minilm"))]:
        print(f"\n=== {name} ===", file=sys.stderr)
        t0 = time.time()
        try:
            fn = builder()
        except Exception as e:
            print(f"  SKIPPED ({e})", file=sys.stderr)
            continue
        build_s = time.time() - t0
        t0 = time.time()
        r = recall_at_k(fn, 5)
        query_s = time.time() - t0
        r["build_seconds"] = round(build_s, 1)
        r["query_seconds_total"] = round(query_s, 2)
        results[name] = r
        print(f"  recall@1={r['recall@1']}  recall@5={r['recall@5']}  "
              f"build={r['build_seconds']}s  query={r['query_seconds_total']}s "
              f"({len(r['misses'])} misses)", file=sys.stderr)
        for q, exp, got in r["misses"]:
            print(f"    MISS: '{q}' expected '{exp}', got {got}", file=sys.stderr)

    print("\n\n=== SUMMARY ===")
    for name, r in results.items():
        print(f"{name:10s} recall@1={r['recall@1']:.3f} recall@5={r['recall@5']:.3f} "
              f"build={r['build_seconds']}s query_total={r['query_seconds_total']}s")


if __name__ == "__main__":
    main()
