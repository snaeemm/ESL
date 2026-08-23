"""OPTIONAL local embedding retrieval experiment (Layer 4b).

NOT wired into lib/sign_resolver.py by default. This exists to benchmark
whether a local embedding model recovers legitimately more lexical
matches than plain token-overlap retrieval (lib/vocab_retrieval.py),
before deciding whether it's worth keeping permanently, per explicit
instruction: "Keep embeddings only if they materially improve valid
recovery... embedding similarity must never directly authorize a sign."

Model: nomic-embed-text, pulled locally via Ollama (`ollama pull
nomic-embed-text`, ~274MB, runs on the same local Ollama server as
Falcon - no cloud calls, no new Python dependency). Chosen because it is
explicitly documented as effective on short multilingual text, and 768-d
vectors for ~1,143 catalog rows plus a handful of query terms is trivial
to keep in memory - no vector DB needed.

Embeddings are precomputed ONCE per catalog version and cached to disk
(data/zho/catalog_embeddings.json) so a lesson run never re-embeds all
1,143 entries - see scripts/vocab_embedding_benchmark.py for the
precompute step and the recover-vs-mislead benchmark itself.

Exactly like lib/vocab_retrieval.py's token-overlap retrieval, this module
ONLY proposes candidates. Nothing here selects or authorizes a sign -
that remains Falcon's constrained choice (from the SAME candidate set,
shown its stable ids) plus lib/sign_resolver.py's deterministic
verification, unchanged.
"""
import json
import math
import os

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")
EMBEDDINGS_CACHE_PATH = os.path.join(ROOT, "data", "zho", "catalog_embeddings.json")
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def _embed_text(text: str, model: str = EMBED_MODEL) -> list:
    r = requests.post(OLLAMA_EMBED_URL, json={"model": model, "prompt": text}, timeout=60)
    r.raise_for_status()
    return r.json()["embedding"]


def _catalog_embedding_text(row: dict) -> str:
    # Bilingual: embed EN and AR label together so a query in either
    # language can retrieve the same row via a single vector.
    parts = [row.get("word_en") or "", row.get("word_ar") or "", row.get("category") or ""]
    return " | ".join(p for p in parts if p)


def precompute_catalog_embeddings(force: bool = False) -> dict:
    """Returns {catalog_id: embedding_vector}. Loads from cache unless
    force=True or the cache doesn't match the current catalog size."""
    with open(CATALOG_PATH, encoding="utf-8") as f:
        rows = json.load(f)

    if not force and os.path.exists(EMBEDDINGS_CACHE_PATH):
        with open(EMBEDDINGS_CACHE_PATH, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("catalog_size") == len(rows):
            return cached["embeddings"]

    embeddings = {}
    for i, row in enumerate(rows):
        text = _catalog_embedding_text(row)
        if not text:
            continue
        embeddings[row["id"]] = _embed_text(text)
        if (i + 1) % 100 == 0:
            print(f"  embedded {i + 1}/{len(rows)}...")

    with open(EMBEDDINGS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"catalog_size": len(rows), "model": EMBED_MODEL, "embeddings": embeddings}, f)
    return embeddings


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class EmbeddingIndex:
    def __init__(self):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            self.rows = json.load(f)
        self.by_id = {r["id"]: r for r in self.rows}
        self.embeddings = precompute_catalog_embeddings()

    def retrieve_candidates(self, term: str, top_n: int = 5, min_similarity: float = 0.55) -> list:
        q = _embed_text(term)
        scored = []
        for catalog_id, vec in self.embeddings.items():
            sim = _cosine(q, vec)
            if sim >= min_similarity:
                scored.append((sim, self.by_id[catalog_id]))
        scored.sort(key=lambda x: -x[0])
        return [{"similarity": round(sim, 4), **row} for sim, row in scored[:top_n]]


_INDEX = None


def get_embedding_index() -> "EmbeddingIndex":
    global _INDEX
    if _INDEX is None:
        _INDEX = EmbeddingIndex()
    return _INDEX
