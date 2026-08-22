"""SOURCE stage (build order Step 2) + source-language detection (Step 3).

Loads a plain .md/.txt academic source file, assigns it a stable SHA-256
identity, and detects/declares its language. The academic source text
itself is never modified anywhere downstream - every later stage carries
a reference back to source_id/source_path, never a copy that could drift.
"""
import hashlib
import os
import re
import time

SUPPORTED_EXTENSIONS = (".md", ".txt")

# Deterministic language detection: Arabic script vs Latin script, by
# character-class ratio. No model is used for this - the brief explicitly
# says a large model is not warranted solely for language detection, and
# script-range counting is a fully deterministic, auditable heuristic that
# is more than sufficient to distinguish English from Arabic/MSA source
# text (the only two languages this prototype needs to support).
_ARABIC_RANGE = re.compile(r"[؀-ۿݐ-ݿ]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    arabic_chars = len(_ARABIC_RANGE.findall(text))
    latin_chars = len(_LATIN_LETTER.findall(text))
    if arabic_chars == 0 and latin_chars == 0:
        return "unknown"
    return "ar" if arabic_chars > latin_chars else "en"


def load_source(path: str, language: str = "auto") -> dict:
    """Loads a source file and returns its manifest dict.

    language: "auto" | "en" | "ar" — "auto" runs detect_language() on the
    loaded text; "en"/"ar" is a caller-declared override, stored as-is
    (still deterministic, still auditable — the manifest records which
    mode was used).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported source file type '{ext}'. Supported: {SUPPORTED_EXTENSIONS}"
        )
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Source file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    source_id = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    if language == "auto":
        resolved_language = detect_language(text)
        language_mode = "auto-detected"
    elif language in ("en", "ar"):
        resolved_language = language
        language_mode = "user-declared"
    else:
        raise ValueError(f"Unsupported --source-language value: {language!r} (use auto|en|ar)")

    return {
        "source_id": source_id,
        "source_path": os.path.abspath(path),
        "source_language": resolved_language,
        "source_language_mode": language_mode,
        "source_text": text,
        "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_source_manifest(manifest: dict, out_path: str) -> None:
    """Writes the manifest WITHOUT the full source_text body (that stays
    the single canonical copy at source_path) - the manifest is a pointer
    + hash + metadata record, not a duplicate of the source itself, so
    there is exactly one place the academic facts actually live."""
    import json
    record = {k: v for k, v in manifest.items() if k != "source_text"}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
