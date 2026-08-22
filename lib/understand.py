"""UNDERSTAND stage (build order Step 4).

Reusable application logic extracted from the proven benchmark script
`benchmarks/llm_grounding/run_ch3_benchmark.py`. The benchmark script
itself is left completely unmodified as evidence — this module reimplements
the same prompt structure, the same Ollama call shape, and the same
<think>-stripping/JSON-array parsing, generalized to take arbitrary source
text instead of the hardcoded Ch.3 path, and to work for either English or
Arabic source text (the prompt itself is language-agnostic: it asks the
model to extract concepts using only the language the source is written
in, not to translate).

Falcon-H1-7B-Instruct was selected here because it won the grounding
benchmark on every metric the brief names (see
benchmarks/llm_grounding/results/ch3_benchmark_results_v3_FINAL.log).
No other model is called by this module.
"""
import json
import re

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M"

# Same rules as the benchmark's SYSTEM_PROMPT, generalized: "the language
# the source is written in" replaces an implicit English assumption, since
# this module must also work on an Arabic/MSA source per the brief's
# source-language-independence requirement.
SYSTEM_PROMPT = """You are a strict content-extraction assistant. You will be given a verified source text.
Extract the key educational concepts as a structured JSON array. Each item must have exactly these fields:
- "concept": a short name for the concept, in the same language as the source text (string)
- "key_terms": a list of important vocabulary words for this concept, in the same language as the source text (list of strings)
- "source_span": a VERBATIM quote copied exactly from the source text that supports this concept (string)

Rules:
- Only use information that is literally present in the source text. Do not add outside knowledge.
- Do not translate the source text. Keep "concept" and "key_terms" in the same language the source text is written in.
- "source_span" MUST be an exact substring of the source text, character for character.
- Output ONLY a JSON array, no other text, no markdown code fences.
"""


class UnderstandError(RuntimeError):
    pass


def _call_ollama(source_text: str, model: str) -> str:
    prompt = f"{SYSTEM_PROMPT}\n\nSOURCE TEXT:\n{source_text}\n\nJSON array:"
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.0, "num_predict": 6000, "repeat_penalty": 1.3},
            },
            timeout=300,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise UnderstandError(
            "Could not reach local Ollama server at http://localhost:11434 — "
            "is Ollama running? (`ollama serve`)"
        ) from e
    except requests.exceptions.HTTPError as e:
        raise UnderstandError(
            f"Ollama returned an error for model '{model}' — is it pulled? "
            f"(`ollama pull {model}`) Detail: {e}"
        ) from e
    return r.json()["response"]


def _parse_json_array(raw: str):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def verify_source_spans(items: list, source_text: str) -> list:
    """Deterministic gate: every claimed source_span must be an exact
    substring of the real source text. This is the one check that
    directly enforces the brief's core traceability requirement — a
    model claiming a quote that isn't really there gets flagged, never
    silently trusted or silently repaired."""
    verified = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        span = item.get("source_span", "")
        is_verified = bool(span) and span.strip() in source_text
        verified.append({
            **item,
            "source_span_verified": is_verified,
            "review_required": not is_verified,
        })
    return verified


def extract_concepts(source_text: str, model: str = DEFAULT_MODEL) -> dict:
    """Runs UNDERSTAND on source_text with the given local Ollama model.

    Returns {"model": ..., "raw_response": ..., "json_parsed": bool,
    "concepts": [...]} where each concept dict has source_span_verified /
    review_required set by verify_source_spans(). Never raises on a
    parse failure — an empty/unparseable extraction is itself a valid,
    reportable outcome (mirrors jais-adaptive's documented failure mode
    in the benchmark), not something to hide.
    """
    raw = _call_ollama(source_text, model)
    items = _parse_json_array(raw)
    concepts = verify_source_spans(items, source_text) if items is not None else []
    return {
        "model": model,
        "raw_response": raw,
        "json_parsed_successfully": items is not None,
        "num_concepts_extracted": len(concepts),
        "concepts": concepts,
    }
