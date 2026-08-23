"""OPTIONAL local multilingual sentence-embedding retrieval (Layer 4b),
sentence-transformers backend.

Deliberately separate from lib/vocab_embedding.py (the earlier Ollama/
nomic-embed-text experiment) so both can be benchmarked against each
other and against plain lexical retrieval before anything is kept
permanently - per explicit instruction to compare at least two
lightweight multilingual sentence-embedding models, prefer the smallest
one that performs adequately on OUR bilingual ZHO catalog, and never let
embedding similarity itself authorize a sign (Falcon still chooses only
from the retrieved candidate ids, or NONE; lib/sign_resolver.py still
deterministically verifies the choice).

Model choice rationale: the catalog is bilingual (EN/AR) and small
(~1,143 rows), and sign-plan items can be short phrases, not just single
words, so what's needed is multilingual SENTENCE/phrase embeddings, not
raw LLM capability - hence sentence-transformers rather than routing this
through Falcon or Ollama. Two lightweight multilingual candidates are
compared here (see scripts/vocab_embedding_benchmark.py for the actual
Recall@1/Recall@5 numbers on our data before either is trusted):

  - intfloat/multilingual-e5-small   (~118M params, 384-d)
  - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
    (~118M params, 384-d)

Both are small enough that embedding all 1,143 catalog rows takes
seconds on CPU, and are commonly used as strong lightweight multilingual
retrieval baselines - not chosen "by reputation alone", chosen because
they are the standard small-model starting point and then actually
measured against our data.
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")

MODELS = {
    "e5-small": "intfloat/multilingual-e5-small",
    "minilm": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
}

_MODEL_CACHE = {}
_ENCODER_CACHE = {}


def _get_model(model_key: str):
    if model_key not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer
        _MODEL_CACHE[model_key] = SentenceTransformer(MODELS[model_key])
    return _MODEL_CACHE[model_key]


def _catalog_text(row: dict, for_query: bool = False, model_key: str = "e5-small") -> str:
    if model_key == "e5-small":
        # e5 models are trained with an explicit "query:"/"passage:"
        # instruction prefix - omitting it measurably hurts retrieval
        # quality for this model family.
        prefix = "query: " if for_query else "passage: "
    else:
        prefix = ""
    if for_query:
        return prefix + row  # row is already the raw query text here
    parts = [row.get("word_en") or "", row.get("word_ar") or "", row.get("category") or ""]
    return prefix + " | ".join(p for p in parts if p)


class STEmbeddingIndex:
    def __init__(self, model_key: str):
        assert model_key in MODELS, f"unknown model_key {model_key!r}, choose from {list(MODELS)}"
        self.model_key = model_key
        self.model = _get_model(model_key)
        with open(CATALOG_PATH, encoding="utf-8") as f:
            self.rows = [r for r in json.load(f) if r.get("word_en") or r.get("word_ar")]
        self.by_id = {r["id"]: r for r in self.rows}

        cache_path = os.path.join(ROOT, "data", "zho", f"catalog_embeddings_{model_key}.npz")
        if os.path.exists(cache_path):
            data = np.load(cache_path, allow_pickle=True)
            if list(data["ids"]) == [r["id"] for r in self.rows]:
                self.ids = list(data["ids"])
                self.vectors = data["vectors"]
                return

        texts = [_catalog_text(r, for_query=False, model_key=model_key) for r in self.rows]
        self.vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        self.ids = [r["id"] for r in self.rows]
        np.savez(cache_path, ids=np.array(self.ids, dtype=object), vectors=self.vectors)

    def retrieve_candidates(self, term: str, top_n: int = 5) -> list:
        q_text = _catalog_text(term, for_query=True, model_key=self.model_key)
        q_vec = self.model.encode([q_text], normalize_embeddings=True, show_progress_bar=False)[0]
        sims = self.vectors @ q_vec
        order = np.argsort(-sims)[:top_n]
        return [{"similarity": round(float(sims[i]), 4), **self.by_id[self.ids[i]]} for i in order]


_INDEX_CACHE = {}


def get_index(model_key: str) -> STEmbeddingIndex:
    if model_key not in _INDEX_CACHE:
        _INDEX_CACHE[model_key] = STEmbeddingIndex(model_key)
    return _INDEX_CACHE[model_key]
