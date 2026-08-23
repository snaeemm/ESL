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
- "concept" must be a short plain label (1-4 words), never a slug, never mixing scripts (no underscores joining words, no embedded Latin words inside an Arabic concept, no slashes).
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
    """Strict parse + bounded surrounding-text extraction only - no
    repair of the JSON content itself happens here (that would risk
    silently inventing/mangling model output). Returns (parsed_or_None,
    extraction_used: bool)."""
    stripped = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    try:
        parsed = json.loads(stripped)
        return parsed, False
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", stripped, re.DOTALL)
    if not match:
        return None, True
    try:
        return json.loads(match.group()), True
    except json.JSONDecodeError:
        return None, True


def _validate_schema(items) -> bool:
    """Deterministic schema check (brief §L step 4): every item must be a
    dict with concept (str), key_terms (list of str), source_span (str).
    A structurally-broken array (wrong types, missing fields) is treated
    the same as a parse failure - it must not silently pass through with
    missing data."""
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("concept"), str) or not item.get("concept"):
            return False
        if not isinstance(item.get("key_terms"), list) or not all(isinstance(t, str) for t in item.get("key_terms")):
            return False
        if not isinstance(item.get("source_span"), str) or not item.get("source_span"):
            return False
    return True


REPAIR_PROMPT_TEMPLATE = """Your previous response was supposed to be a JSON array but was invalid or malformed. \
Here is exactly what you produced:

{broken}

Re-output ONLY a corrected, strictly valid JSON array with the same schema as before: each item must have \
"concept" (string), "key_terms" (list of strings), "source_span" (string, an exact verbatim substring of the \
original source text). Do not add commentary, markdown fences, or explanation. If you cannot reconstruct valid \
content, output an empty JSON array: []
"""


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

    Bounded structured-output handling (brief §L): strict parse -> safe
    extraction from surrounding text if needed -> schema validation ->
    ONE bounded repair/retry re-prompting the model with its own broken
    output -> deterministic REVIEW/BLOCKED failure (empty concepts) if
    still invalid. No unbounded retry loop, no silent JSON repair of the
    model's actual content.

    Returns {"model", "raw_response", "json_parsed_successfully",
    "num_concepts_extracted", "concepts", "structured_output_trace"}
    where structured_output_trace records the initial parse/extraction/
    schema outcome and whether a repair retry ran and its result, for
    traceability. Never raises on a parse failure — an empty/unparseable
    extraction is itself a valid, reportable outcome, not something to
    hide.
    """
    raw = _call_ollama(source_text, model)
    items, extraction_used = _parse_json_array(raw)
    initial_valid = items is not None and _validate_schema(items)

    trace = {
        "initial_parse_success": items is not None,
        "initial_extraction_used": extraction_used,
        "initial_schema_valid": initial_valid,
        "repair_retry_attempted": False,
        "repair_retry_parse_success": None,
        "final_parse_status": "OK" if initial_valid else None,
    }

    if not initial_valid:
        trace["repair_retry_attempted"] = True
        repair_prompt = REPAIR_PROMPT_TEMPLATE.format(broken=raw[:4000])
        try:
            repaired_raw = _call_ollama(repair_prompt, model)
            repaired_items, repaired_extraction_used = _parse_json_array(repaired_raw)
            repaired_valid = repaired_items is not None and _validate_schema(repaired_items)
        except UnderstandError:
            repaired_items, repaired_valid, repaired_raw = None, False, None

        trace["repair_retry_parse_success"] = repaired_valid
        if repaired_valid:
            items = repaired_items
            raw = f"{raw}\n\n--- REPAIR RETRY RESPONSE ---\n{repaired_raw}"
            trace["final_parse_status"] = "OK_AFTER_REPAIR"
        else:
            items = []
            trace["final_parse_status"] = "FAILED_AFTER_REPAIR"

    concepts = verify_source_spans(items, source_text) if items else []
    return {
        "model": model,
        "raw_response": raw,
        "json_parsed_successfully": trace["final_parse_status"] in ("OK", "OK_AFTER_REPAIR"),
        "num_concepts_extracted": len(concepts),
        "concepts": concepts,
        "structured_output_trace": trace,
    }
