"""SEMANTIC SIGN PLAN stage (build order Step 6 — required change from the
key-terms-only approach).

For each episode unit, derives a small ordered list of semantic items
(concepts/actions/entities) that together communicate the unit's
educational meaning — not just its literal key_terms. This is explicitly
NOT a claim of validated Arabic Sign Language grammar or word order; it
is a semantic plan a downstream deterministic resolver can attach real
signs/fingerspelling to. Anything the model is unsure about is marked
uncertain, not silently smoothed over.
"""
import json
import re

from lib.episode_builder import _call_ollama_raw, _parse_json_array
from lib.understand import UnderstandError

SIGN_PLAN_SYSTEM_PROMPT = """You are helping plan a sign-language video for a school lesson.
You will be given one educational sentence, its concept name, and its key_terms, all grounded in a
verified academic source.

Break the sentence's MEANING down into a short ordered list of semantic items — the core
entities/actions/relationships that must be communicated, not just a list of nouns. Prefer verbs and
relationships over dropping them. Each item is a short word or phrase in the SAME language as the
input sentence.

Example (English input "The membrane controls what enters and leaves the cell."):
["MEMBRANE", "CONTROL/REGULATE", "ENTER", "LEAVE", "CELL"]

Rules:
- 3 to 7 items per sentence. Do not pad or invent content not implied by the sentence.
- Do not include grammatical function words (the, a, of, that) as separate items.
- If you are not confident a faithful semantic breakdown is possible for this sentence, output
  an empty array [] instead of guessing.

Output ONLY a JSON array of strings. No other text, no markdown code fences.
"""


def build_sign_plan(unit: dict, model: str) -> dict:
    """Returns the unit augmented with a "semantic_sign_plan" list and a
    "semantic_plan_status" of either "OK" or "REVIEW_REQUIRED" (model
    declined / returned empty / call failed)."""
    if not unit.get("educational_sentence"):
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": "no educational_sentence available to plan from"}

    prompt_input = {
        "concept": unit["concept"],
        "key_terms": unit.get("key_terms", []),
        "educational_sentence": unit["educational_sentence"],
    }
    prompt = f"{SIGN_PLAN_SYSTEM_PROMPT}\n\nINPUT:\n{json.dumps(prompt_input, ensure_ascii=False)}\n\nJSON array:"
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": f"local model call failed: {e}"}

    items = _parse_json_array(raw)
    if items is None or not isinstance(items, list):
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": "model output was not a parseable JSON array"}

    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return {**unit, "semantic_sign_plan": [], "semantic_plan_status": "REVIEW_REQUIRED",
                "semantic_plan_reason": "model declined to produce a semantic breakdown (returned empty)"}

    return {**unit, "semantic_sign_plan": items, "semantic_plan_status": "OK"}


def build_sign_plans(units: list, model: str) -> list:
    return [build_sign_plan(u, model) for u in units]
