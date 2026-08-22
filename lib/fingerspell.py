"""FINGERSPELLING FALLBACK (build order Step 9).

Fully deterministic: decomposes an Arabic word into base letters and
looks each one up in data/zho/arabic_alphabet_map.json against the real
verified ZHO Alphabets catalog entries. No model involvement at all in
this module — by the time a word reaches here, terminology.py has
already produced (and sanity-checked) the Arabic term; this module only
ever spells letters that are already text.

Fingerspelling is explicitly a FALLBACK, never presented as equivalent
to a verified lexical sign — every result carries fallback_type="FINGERSPELL"
and the caller (sign_resolver.py) is responsible for keeping that
distinct from VERIFIED_SIGN in the final unit status.
"""
import json
import os
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALPHABET_MAP_PATH = os.path.join(ROOT, "data", "zho", "arabic_alphabet_map.json")
CATALOG_PATH = os.path.join(ROOT, "data", "zho", "catalog.json")

# Normalizes alif variants (with hamza/madda) to the plain alif entry for
# fingerspelling purposes, and strips Arabic diacritics (tashkeel) before
# decomposition — ZHO's Alphabets set has no separate entries for these,
# and coverage_report.md's own ambiguity notes concern base letters, not
# diacritic marks.
_ALIF_VARIANTS = {"أ": "ا", "إ": "ا", "آ": "ا"}
_TASHKEEL = "".join(chr(c) for c in range(0x064B, 0x0653)) + "ٰ"


def _load_alphabet_map() -> dict:
    with open(ALPHABET_MAP_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {entry["letter"]: entry for entry in data["letters"]}


_ALPHABET_MAP = None
_CATALOG_BY_ID = None


def _get_map() -> dict:
    global _ALPHABET_MAP
    if _ALPHABET_MAP is None:
        _ALPHABET_MAP = _load_alphabet_map()
    return _ALPHABET_MAP


def _get_catalog_by_id() -> dict:
    """Full catalog rows keyed by id — needed because
    arabic_alphabet_map.json only stores catalog_id, not the full row
    (video_url, category, etc.) that lib/clip_prep.py needs to actually
    download/trim the letter's clip."""
    global _CATALOG_BY_ID
    if _CATALOG_BY_ID is None:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            rows = json.load(f)
        _CATALOG_BY_ID = {r["id"]: r for r in rows}
    return _CATALOG_BY_ID


def _strip_diacritics(word: str) -> str:
    return "".join(c for c in word if c not in _TASHKEEL)


def decompose_letters(arabic_word: str) -> list:
    """Returns the ordered list of base-form Arabic letters in the word,
    normalizing alif-hamza variants but NOT decomposing the 'al'/'laa'
    ligature entries (they're signed as whole units when explicitly
    chosen, not produced automatically by decomposition)."""
    word = _strip_diacritics(arabic_word.strip())
    word = unicodedata.normalize("NFC", word)
    letters = []
    for ch in word:
        if ch in (" ", "‏", "‎"):
            continue
        ch = _ALIF_VARIANTS.get(ch, ch)
        letters.append(ch)
    return letters


def fingerspell(arabic_word: str) -> dict:
    """Returns a dict describing whether arabic_word can be fully
    fingerspelled from verified ZHO alphabet clips.

    {
      "arabic_word": "...",
      "letters": ["kh", "l", "y", "t"],           # name_ar per letter, in order
      "catalog_refs": [{"letter": "خ", "catalog_id": "...", "word_en": "Khaa"}, ...],
      "fully_resolved": bool,
      "unresolved_letters": [...]                  # letters with no catalog entry, if any
    }
    """
    alphabet_map = _get_map()
    letters = decompose_letters(arabic_word)
    catalog_refs = []
    unresolved = []
    for ch in letters:
        entry = alphabet_map.get(ch)
        if entry is None:
            unresolved.append(ch)
            continue
        catalog_row = _get_catalog_by_id().get(entry["catalog_id"])
        catalog_refs.append({
            "letter": ch,
            "name_ar": entry["name_ar"],
            "word_en": entry["word_en"],
            "catalog_id": entry["catalog_id"],
            "catalog_row": catalog_row,  # full row (id, category, video_url, ...) for clip_prep.py
        })
    return {
        "arabic_word": arabic_word,
        "letters": [c["name_ar"] for c in catalog_refs],
        "catalog_refs": catalog_refs,
        "fully_resolved": len(unresolved) == 0 and len(letters) > 0,
        "unresolved_letters": unresolved,
    }
