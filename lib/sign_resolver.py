"""DETERMINISTIC SIGN RESOLUTION (build order Step 8) + coverage report.

Resolves each semantic_sign_plan item against data/zho/catalog.json using
the SAME exact case-insensitive word_en matching approach already
validated in data/zho/coverage_report.md §4 and used by
scripts/zho_download.py — substring/fuzzy matching was explicitly tried
there and rejected as unreliable (e.g. "cell" matching "excellent"), so
this module does not reintroduce it.

No model is involved in this module. Falcon never sees catalog.json and
never chooses a sign — it only produced the semantic plan / terminology
text upstream. That separation is deliberate and is what "the LLM must
not invent a sign" means in practice here.
"""
import json
import os

from lib.fingerspell import fingerspell
from lib.terminology import resolve_terminology

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")

STATUS_VERIFIED = "VERIFIED_SIGN"
STATUS_FINGERSPELL = "FINGERSPELL_CANDIDATE"
STATUS_UNSUPPORTED = "UNSUPPORTED"
STATUS_REVIEW = "REVIEW_REQUIRED"


def _load_catalog_index() -> dict:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        rows = json.load(f)
    index = {}
    for r in rows:
        index.setdefault(r["word_en"].strip().lower(), []).append(r)
    return index


_CATALOG_INDEX = None


def _get_catalog_index() -> dict:
    global _CATALOG_INDEX
    if _CATALOG_INDEX is None:
        _CATALOG_INDEX = _load_catalog_index()
    return _CATALOG_INDEX


def _match_verified_sign(term_en: str):
    """Exact case-insensitive word_en match only. Returns the first
    matching catalog row, or None. Multiple entries for the same word_en
    (e.g. a homograph across categories) are possible in principle;
    picking the first is a documented, simple prototype choice — see
    README known limitations. Never picks a DIFFERENT word merely
    because it seems semantically close (rule 7 of Step 8)."""
    matches = _get_catalog_index().get(term_en.strip().lower())
    return matches[0] if matches else None


def resolve_item(item_text: str, source_language: str, source_span: str,
                  educational_sentence: str, model: str) -> dict:
    """Resolves one semantic_sign_plan item end-to-end: try a verified
    ZHO lexical match first (on the item text as given, and — for
    English sources — also tried as-is since some ZHO entries are English
    labels); if no match, fall back to Arabic fingerspelling via
    terminology.py + fingerspell.py."""
    # 1. Verified lexical sign — deterministic exact match, no translation
    #    needed even for an English item, since catalog.json's word_en is
    #    itself English-labeled (matches coverage_report.md's own method).
    direct_match = _match_verified_sign(item_text)
    if direct_match:
        return {
            "term": item_text,
            "status": STATUS_VERIFIED,
            "catalog_ref": direct_match,
            "fallback_type": None,
            "match_reason": f"exact case-insensitive match against catalog.json word_en='{direct_match['word_en']}'",
            "review_required": False,
        }

    # 2. No lexical match -> attempt Arabic fingerspelling fallback.
    term_info = resolve_terminology(item_text, source_language, source_span, educational_sentence, model)
    if term_info["translation_status"] not in ("OK", "NOT_NEEDED") or not term_info["arabic_term"]:
        return {
            "term": item_text,
            "status": STATUS_REVIEW,
            "catalog_ref": None,
            "fallback_type": None,
            "terminology": term_info,
            "match_reason": "no verified lexical sign, and Arabic terminology translation was not usable",
            "review_required": True,
        }

    spelled = fingerspell(term_info["arabic_term"])
    if spelled["fully_resolved"]:
        return {
            "term": item_text,
            "status": STATUS_FINGERSPELL,
            "catalog_ref": None,
            "fallback_type": "FINGERSPELL",
            "terminology": term_info,
            "fingerspell": spelled,
            "match_reason": f"no verified lexical sign for '{item_text}'; fingerspelled Arabic term '{term_info['arabic_term']}' — all letters resolved against data/zho/arabic_alphabet_map.json",
            "review_required": False,
        }

    return {
        "term": item_text,
        "status": STATUS_UNSUPPORTED,
        "catalog_ref": None,
        "fallback_type": "FINGERSPELL",
        "terminology": term_info,
        "fingerspell": spelled,
        "match_reason": f"no verified lexical sign, and fingerspelling '{term_info['arabic_term']}' left unresolved letters {spelled['unresolved_letters']}",
        "review_required": True,
    }


def resolve_unit(unit: dict, source_language: str, model: str) -> dict:
    resolutions = [
        resolve_item(item, source_language, unit["source_span"], unit.get("educational_sentence", ""), model)
        for item in unit.get("semantic_sign_plan", [])
    ]
    unit_review_required = unit.get("review_required", False) or any(r["review_required"] for r in resolutions)
    return {**unit, "sign_resolution": resolutions, "review_required": unit_review_required}


def resolve_units(units: list, source_language: str, model: str) -> list:
    return [resolve_unit(u, source_language, model) for u in units]


def coverage_report(units: list) -> dict:
    """Two SEPARATE coverage numbers per Step 9 — never conflated:
    verified_lexical_sign_coverage_pct measures REAL ZHO dictionary
    signs only; renderable_coverage_with_fallback_pct additionally
    counts fingerspelled items as "renderable" but explicitly NOT as
    "sign-language accuracy" (documented in the returned dict itself so
    the distinction travels with the data)."""
    all_resolutions = [r for u in units for r in u.get("sign_resolution", [])]
    total = len(all_resolutions)
    verified = sum(1 for r in all_resolutions if r["status"] == STATUS_VERIFIED)
    fingerspell_ok = sum(1 for r in all_resolutions if r["status"] == STATUS_FINGERSPELL)
    unsupported = sum(1 for r in all_resolutions if r["status"] == STATUS_UNSUPPORTED)
    review = sum(1 for r in all_resolutions if r["status"] == STATUS_REVIEW)

    lexical_pct = round(100.0 * verified / total, 1) if total else 0.0
    renderable_pct = round(100.0 * (verified + fingerspell_ok) / total, 1) if total else 0.0

    return {
        "total_sign_units": total,
        "verified_signs": verified,
        "fallback_candidates": fingerspell_ok,
        "unsupported_units": unsupported,
        "review_required_units": review,
        "verified_lexical_sign_coverage_pct": lexical_pct,
        "renderable_coverage_with_fallback_pct": renderable_pct,
        "_note": (
            "renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, "
            "NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a "
            "verified lexical sign — see fallback_type on each resolution."
        ),
    }
