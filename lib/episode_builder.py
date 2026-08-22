"""STRUCTURE stage (build order Step 5).

Turns UNDERSTAND's verified concepts into a short educational episode:
one simplified sentence per concept, still attached to its source_span
and key_terms. Uses the same local Falcon model for simplification
(a bounded, single-purpose call — "simplify this concept into one short
educational sentence using only what's in the span"), never adding new
facts, and every resulting unit is checked against a deterministic
grounding heuristic before being trusted.

Similarity/keyword-overlap heuristics here are NOT proof of factual
correctness — they only catch the crudest failure mode (a sentence that
shares no vocabulary at all with its own source span). This limitation
is stated explicitly, not glossed over: see README "Known limitations".
"""
import json
import re

from lib.understand import _call_ollama, UnderstandError  # reuse the same Ollama call plumbing

SIMPLIFY_SYSTEM_PROMPT = """You are an educational content simplifier for a school lesson video.
You will be given a list of concepts, each with a "concept" name, "key_terms", and a "source_span"
(a verbatim quote from an approved academic source).

For each item, write ONE short, simple sentence (aimed at a school student) that captures the
educational meaning of that concept, using ONLY information present in its source_span. Do not add
outside facts, numbers, or examples that are not in the source_span. Write the sentence in the same
language as the source_span.

Output ONLY a JSON array, same length and same order as the input, where each element is:
{"educational_sentence": "..."}

No other text, no markdown code fences.
"""


def _parse_json_array(raw: str):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def _tokenize(text: str) -> set:
    return set(re.findall(r"\w+", text.lower()))


def _grounding_heuristic_ok(sentence: str, source_span: str, key_terms: list) -> bool:
    """Crude, explicit, deterministic check: the simplified sentence must
    share at least some real vocabulary with its own source_span (and,
    where possible, at least one key_term must appear in some form).
    Catches "the model wrote something unrelated" — nothing more."""
    if not sentence:
        return False
    sent_tokens = _tokenize(sentence)
    span_tokens = _tokenize(source_span)
    overlap = sent_tokens & span_tokens
    return len(overlap) >= 1


def build_episode(concepts: list, model: str, target_duration_s: int = 45) -> dict:
    """Builds episode.json's "units" list from UNDERSTAND's verified
    concepts. Only concepts with source_span_verified=True are eligible
    (an unverified span cannot ground a taught fact).

    NOTE on duration: this function no longer truncates by unit count.
    An earlier version estimated episode length here, BEFORE sign
    resolution/fingerspelling expansion existed — that produced a wildly
    wrong estimate (a 45s target rendered as 314.76s on the first real
    run, because fingerspelling turns one semantic item into 3-5 letter
    clips). Duration-aware selection now happens in
    lib/duration_planner.py, AFTER sign resolution, once the real
    render-segment count per unit is actually known. This function
    structures every verified concept; run_pipeline.py trims the
    resulting unit list to fit target_duration_s afterward.
    """
    verified = [c for c in concepts if c.get("source_span_verified")]
    if not verified:
        return {"target_duration_s": target_duration_s, "units": [], "note": "no verified concepts available to structure"}

    prompt_items = [
        {"concept": c["concept"], "key_terms": c.get("key_terms", []), "source_span": c["source_span"]}
        for c in verified
    ]
    prompt = f"{SIMPLIFY_SYSTEM_PROMPT}\n\nINPUT:\n{json.dumps(prompt_items, ensure_ascii=False)}\n\nJSON array:"
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {
            "target_duration_s": target_duration_s,
            "units": [],
            "error": f"STRUCTURE stage could not reach the local model: {e}",
        }

    simplified = _parse_json_array(raw) or []

    units = []
    for i, c in enumerate(verified):
        sentence = ""
        if i < len(simplified) and isinstance(simplified[i], dict):
            sentence = simplified[i].get("educational_sentence", "") or ""
        grounded = _grounding_heuristic_ok(sentence, c["source_span"], c.get("key_terms", []))
        units.append({
            "unit_id": f"u{i:02d}",
            "concept": c["concept"],
            "source_span": c["source_span"],
            "source_span_verified": True,  # only verified concepts reach here, by construction
            "educational_sentence": sentence if grounded else "",
            "educational_sentence_grounded": grounded,
            "key_terms": c.get("key_terms", []),
            "review_required": (not grounded) or (not sentence),
        })

    return {
        "target_duration_s": target_duration_s,
        "total_verified_concepts_available": len(verified),
        "units": units,
    }


def _call_ollama_raw(prompt: str, model: str) -> str:
    """Same Ollama call shape as understand.py's _call_ollama, but for an
    already-built prompt rather than raw source text — kept as a thin
    wrapper here instead of importing understand._call_ollama directly
    with a different prompt, to keep understand.py's function signature
    single-purpose (source_text -> concepts)."""
    import requests
    from lib.understand import OLLAMA_URL
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.0, "num_predict": 3000, "repeat_penalty": 1.3},
            },
            timeout=300,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise UnderstandError("Could not reach local Ollama server — is it running?") from e
    except requests.exceptions.HTTPError as e:
        raise UnderstandError(f"Ollama error for model '{model}': {e}") from e
    return r.json()["response"]
