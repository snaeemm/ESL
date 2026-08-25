# Traceability Examples (Release Audit)

Two real examples pulled directly from `outputs/webapp_jobs/`, quoted verbatim from
the actual JSON/Markdown artifacts on disk. No numbers or text below are invented.

---

## Example 1 — Full clean chain (source span -> ... -> final video)

**Job:** `outputs/webapp_jobs/bdff1892c9da/`
**Source:** `content/test_h2_showcase_part2.md` ("A Day With My Family (Part 2)")
**Source SHA-256:** `sha256:48fb43d21310c804e8de554558a2f8e4120b319c767dba2e6a5b4cf5c814a0f3`

Chain for the word "HOT" in unit `u00`:

1. **Source span** (verbatim substring of the source .md, `source_span_verified: true`):
   > "Today the weather is hot, and the sun is bright. Yesterday it was cold, and the rain was heavy."
2. **Concept**: `"Weather Observation"`
3. **Educational sentence** (STRUCTURE stage): `"Today the weather is hot and sunny, while yesterday it was cold and rainy."`
4. **Semantic sign plan item**: `"HOT"`
5. **Resolution / candidate**: exact bilingual match, Layer 1 (no Falcon call needed) — `match_method: "EXACT_EN"`, `information_loss: "FULL"`
6. **Selected sign / authority**: ZHO catalog id `be18e85a-b714-4b5a-9ad7-9cfe9cc0d442`, `word_en: "Hot"`, `word_ar: "حار"`, `source_authority: "INSTITUTIONAL_UAE_REFERENCE"`, `verification_status: "ZHO_INSTITUTIONAL_VERIFIED"`
7. **Rendered segment**: `segment_stem: "005_HOT"`
8. **Final video**: `outputs/webapp_jobs/bdff1892c9da/final_episode.mp4` (exists, 4,886,858 bytes)

Exact `traceability.json` row (from `outputs/webapp_jobs/bdff1892c9da/traceability.json`):

```json
{
  "segment_stem": "005_HOT",
  "sign_decision": {
    "term": "HOT",
    "status": "VERIFIED_SIGN",
    "match_method": "EXACT_EN",
    "fallback_type": null,
    "catalog_ref": {
      "id": "be18e85a-b714-4b5a-9ad7-9cfe9cc0d442",
      "word_en": "Hot",
      "category": "Attributes and Situations",
      "video_url": "https://player.vimeo.com/external/267562386.sd.mp4?s=95a9f35369c842b525025d7167fe6b75e4cc49a3&profile_id=164",
      "has_video": true,
      "word_ar": "حار",
      "source": "ZHO",
      "word_ar_integrity": "VALID"
    },
    "supplementary_ref": null,
    "fingerspell": null,
    "match_reason": "exact bilingual match: query='HOT' == catalog word_en/word_ar='Hot' / 'حار'",
    "retrieval_trace": { "information_loss": "FULL" }
  },
  "semantic_concept": "Weather Observation",
  "source_span": "Today the weather is hot, and the sun is bright. Yesterday it was cold, and the rain was heavy.",
  "render_source": "ZHO",
  "source_authority": "INSTITUTIONAL_UAE_REFERENCE",
  "verification_status": "ZHO_INSTITUTIONAL_VERIFIED",
  "supporting_sources": [],
  "arabic_caption_source": "ZHO",
  "selected_asset": {
    "zho_stable_id": "be18e85a-b714-4b5a-9ad7-9cfe9cc0d442",
    "word_en": "Hot",
    "word_ar": "حار"
  },
  "selection_reason": "exact bilingual match: query='HOT' == catalog word_en/word_ar='Hot' / 'حار'",
  "gap_reason": null,
  "semantic_sign_plan_item_index": 2,
  "unit_id": "u00",
  "educational_sentence": "Today the weather is hot and sunny, while yesterday it was cold and rainy.",
  "concept": "Weather Observation",
  "source_span_verified": true,
  "source_id": "sha256:48fb43d21310c804e8de554558a2f8e4120b319c767dba2e6a5b4cf5c814a0f3",
  "source_path": ".../outputs/webapp_jobs/_staging_31d4b11c4ac9/test_h2_showcase_part2.md"
}
```

---

## Example 2 — Genuine vocabulary gap, honest fallback failure (not silently dropped)

**Same job:** `outputs/webapp_jobs/bdff1892c9da/`, unit `u03`, concept "Academic Success"
**Source span**: `"My exam was successful, and my family is proud."`
**Educational sentence**: `"I did well on my exam, and my family is proud."`
**Semantic sign plan**: `['I', 'DO WELL', 'ON', 'EXAM', 'FAMILY', 'IS PROUD']`

The word "ON" (Arabic term "على") had no ZHO or ESL Zayed lexical match, and even
fingerspelling failed because one Arabic letter (`ى`) has no catalog alphabet entry.
Rather than silently dropping "ON" from the video, the system flags it explicitly as
`UNSUPPORTED` and surfaces it in `review_required.md`. This is the honest-failure path
working as designed — a concept can be marked unsupported, but it is never invented or
silently deleted.

From `outputs/webapp_jobs/bdff1892c9da/episode.json` (resolution object for "ON"):

```json
{
  "unit_id": "u03",
  "source_span": "My exam was successful, and my family is proud.",
  "concept": "Academic Success",
  "resolution": {
    "term": "ON",
    "status": "UNSUPPORTED",
    "catalog_ref": null,
    "fallback_type": "FINGERSPELL",
    "terminology": {
      "source_term": "ON",
      "arabic_term": "على",
      "model": "hf.co/tiiuae/Falcon-H1-7B-Instruct-GGUF:Q4_K_M",
      "translation_status": "OK",
      "translation_reason": "single clean Arabic term"
    },
    "fingerspell": {
      "arabic_word": "على",
      "letters": ["aeen", "laam"],
      "fully_resolved": false,
      "unresolved_letters": ["ى"]
    },
    "match_reason": "no verified lexical sign, and fingerspelling 'على' left unresolved letters ['ى']",
    "review_required": true,
    "render_source": "FINGERSPELL",
    "source_authority": "NONE",
    "gap_reason": "NO_SUPPORTED_LEXICAL_SIGN",
    "supporting_sources": []
  }
}
```

Corresponding excerpt from `outputs/webapp_jobs/bdff1892c9da/review_required.md`:

```
### u03 — Academic Success
- Source span: "My exam was successful, and my family is proud."
- Educational sentence: "I did well on my exam, and my family is proud."
- Semantic sign plan: ['I', 'DO WELL', 'ON', 'EXAM', 'FAMILY', 'IS PROUD']
...
- `u03` **I** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='I' == supplementary english_meaning/arabic_text='I' / 'أنا' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u03` **DO WELL** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'DO WELL' (Falcon reviewed 1 candidates and answered NONE: The semantic item 'DO WELL' does not match the candidate's category 'Environment'.); fingerspelled Arabic term 'نجحت'
- `u03` **ON** — ❌ UNSUPPORTED
  - reason: no verified lexical sign, and fingerspelling 'على' left unresolved letters ['ى']
- `u03` **EXAM** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='EXAM' == catalog word_en/word_ar='Exam' / 'امتحان'
- `u03` **FAMILY** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='FAMILY' == catalog word_en/word_ar='Family' / 'أسرة'
- `u03` **IS PROUD** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'IS PROUD' ...; fingerspelled Arabic term 'راضٍ'

## Review reasons
- u03: 'ON' UNSUPPORTED — no verified lexical sign, and fingerspelling 'على' left unresolved letters ['ى']
- u03: unit-level review_required flag set
```

This single unit ("Academic Success") is a good compact illustration of the whole
authority hierarchy in one place: `I` resolved via ESL Zayed, `EXAM`/`FAMILY` via ZHO,
`DO WELL`/`IS PROUD` via fingerspelling, and `ON` as a genuine, explicitly-flagged
UNSUPPORTED gap — nothing hallucinated, nothing silently dropped.
