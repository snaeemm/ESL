"""TARGET TERMINOLOGY stage (build order Step 7).

For semantic sign-plan items that have no verified ZHO lexical sign, the
fingerspelling fallback needs an Arabic term to spell (the ZHO Alphabets
category is Arabic-letter fingerspelling — see
data/zho/arabic_alphabet_map.json). If the source is already Arabic/MSA,
the item itself is already in Arabic and no translation is needed.

If the source is English, this module asks the local Falcon model for a
single contextually-appropriate Modern Standard Arabic academic term —
NOT an isolated word-for-word dictionary lookup — using the item's own
educational sentence and source_span as context, per the brief's explicit
requirement. Output is deterministically sanity-checked; anything that
doesn't look like one clean Arabic term is marked REVIEW_REQUIRED rather
than guessed.

Falcon's role here is bounded to producing TEXT (an Arabic word) — it
never touches motion, keypoints, or clip selection, which stay fully
deterministic in sign_resolver.py / fingerspell.py.
"""
import json
import re

from lib.episode_builder import _call_ollama_raw, _parse_json_array
from lib.understand import UnderstandError
from lib.source_loader import detect_language

TERMINOLOGY_SYSTEM_PROMPT = """You are a terminology assistant helping produce Modern Standard Arabic (MSA)
academic vocabulary for a school science lesson, translated FROM an English source.

You will be given: the English source_span (context), the English educational_sentence (context), and
one specific English semantic item that needs an Arabic academic term.

Respond with ONLY the single most appropriate Modern Standard Arabic academic term for that item, in the
context given. One word or short fixed compound term only.

Do not add commentary. Do not give multiple alternatives. Do not add explanation, transliteration, or
English. Output ONLY the Arabic term as plain text, nothing else.
"""

_ARABIC_RANGE = re.compile(r"[؀-ۿ]")
_ARABIC_OR_SPACE_ONLY = re.compile(r"^[؀-ۿ\s]+$")
_MULTI_ALTERNATIVE_MARKERS = ("or", "أو", "/", "،", ",", ";", "(", ")")


def _sanity_check_arabic_term(raw: str) -> tuple:
    """Returns (clean_term_or_None, status, reason).

    Requires the ENTIRE string to be Arabic-script characters and
    whitespace only — not merely "contains some Arabic and no Latin".
    An earlier, looser version of this check (Arabic-present + no-Latin)
    let a stray non-Arabic, non-Latin character (a Hangul character,
    observed on the development Cells source run 2026-08-22) through as
    if it were a clean term. Every character must now be in the Arabic
    Unicode block or whitespace, full stop.
    """
    text = raw.strip().strip('"').strip()
    if not text:
        return None, "REVIEW_REQUIRED", "empty model output"
    if len(text.split("\n")) > 1 or len(text) > 60:
        return None, "REVIEW_REQUIRED", "output looks like commentary/multi-line, not a single term"
    if any(m in text for m in _MULTI_ALTERNATIVE_MARKERS):
        return None, "REVIEW_REQUIRED", "output appears to contain multiple alternatives or punctuation"
    if not _ARABIC_RANGE.search(text):
        return None, "REVIEW_REQUIRED", "output contains no Arabic script"
    if not _ARABIC_OR_SPACE_ONLY.match(text):
        return None, "REVIEW_REQUIRED", "output contains non-Arabic, non-whitespace characters"
    return text, "OK", "single clean Arabic term"


_LATIN_RANGE = re.compile(r"[A-Za-z]")
_LATIN_OR_SPACE_ONLY = re.compile(r"^[A-Za-z\s\-]+$")

ENGLISH_GLOSS_SYSTEM_PROMPT = """You are a bilingual glossary assistant. You will be given a short Arabic
educational-lesson word or phrase (with its sentence context) and must respond with ONLY its single most
natural short ENGLISH gloss (1-3 words) — the plain English concept it names, e.g. "Mother" for "أمي" or
"Photosynthesis" for "التمثيل الضوئي".

This is glossary lookup, NOT literary translation — pick the single most common English name for the
concept, not a paraphrase or definition. Respond with ONLY the English gloss in Latin script, nothing
else — no Arabic, no commentary, no punctuation beyond spaces/hyphens.
"""


def gloss_arabic_to_english(item_text: str, source_span: str, educational_sentence: str, model: str) -> dict:
    """Bounded, CANDIDATE-DISCOVERY-ONLY bridge (never authoritative):
    produces a short English gloss for an Arabic semantic-plan item, so
    lib/sign_resolver.py can additionally search the ZHO/ESL Zayed
    catalogs' ENGLISH word_en/english_meaning side for candidates when
    Arabic-side token-overlap retrieval finds nothing. This exists
    because some ZHO catalog rows have known-corrupted word_ar metadata
    (e.g. Mother/Father/Sister all sharing the same wrong value
    "باب الأسرة") while their word_en label is correct - an Arabic query
    for the SAME concept could otherwise never surface that row as a
    candidate at all, through no fault of the query.

    Whatever this returns is still just ONE MORE CANDIDATE for Falcon's
    existing context-constrained selection + deterministic verification +
    information-loss gate (lib/sign_resolver.py Layers 5-6) - it never
    itself authorizes a sign, and it never touches or fabricates any
    catalog Arabic label. Returns {gloss, status, reason}; status is
    "OK" only for a clean single Latin-script term."""
    prompt_input = {
        "source_span": source_span,
        "educational_sentence": educational_sentence,
        "arabic_item": item_text,
    }
    prompt = f"{ENGLISH_GLOSS_SYSTEM_PROMPT}\n\nINPUT:\n{json.dumps(prompt_input, ensure_ascii=False)}\n\nEnglish gloss:"
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {"gloss": None, "status": "REVIEW_REQUIRED", "reason": f"local model call failed: {e}"}

    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = raw.strip().strip('"').strip()
    if not text or len(text.split("\n")) > 1 or len(text) > 40:
        return {"gloss": None, "status": "REVIEW_REQUIRED", "reason": "output looks like commentary/multi-line, not a single gloss"}
    if _ARABIC_RANGE.search(text):
        return {"gloss": None, "status": "REVIEW_REQUIRED", "reason": "output contains Arabic script, not a clean English gloss"}
    if not _LATIN_OR_SPACE_ONLY.match(text):
        return {"gloss": None, "status": "REVIEW_REQUIRED", "reason": "output contains non-Latin, non-whitespace characters"}
    return {"gloss": text, "status": "OK", "reason": "single clean English gloss"}


def resolve_terminology(item_text: str, source_language: str, source_span: str,
                         educational_sentence: str, model: str) -> dict:
    """item_text: one semantic_sign_plan entry (English or Arabic already,
    per source_language). Returns a record with source_term, arabic_term,
    model, translation_status, translation_reason — always present, even
    when translation wasn't needed or failed."""
    if source_language == "ar" or detect_language(item_text) == "ar":
        # Already Arabic (or the source itself is Arabic/MSA) — preserve
        # the source terminology rather than translating unnecessarily,
        # per the brief's explicit instruction.
        return {
            "source_term": item_text,
            "arabic_term": item_text,
            "model": None,
            "translation_status": "NOT_NEEDED",
            "translation_reason": "source item already in Arabic; preserved as-is",
        }

    prompt_input = {
        "source_span": source_span,
        "educational_sentence": educational_sentence,
        "item_to_translate": item_text,
    }
    prompt = f"{TERMINOLOGY_SYSTEM_PROMPT}\n\nINPUT:\n{json.dumps(prompt_input, ensure_ascii=False)}\n\nArabic term:"
    try:
        raw = _call_ollama_raw(prompt, model)
    except UnderstandError as e:
        return {
            "source_term": item_text, "arabic_term": None, "model": model,
            "translation_status": "REVIEW_REQUIRED",
            "translation_reason": f"local model call failed: {e}",
        }

    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    clean, status, reason = _sanity_check_arabic_term(raw)
    return {
        "source_term": item_text,
        "arabic_term": clean,
        "model": model,
        "translation_status": status,
        "translation_reason": reason,
    }
