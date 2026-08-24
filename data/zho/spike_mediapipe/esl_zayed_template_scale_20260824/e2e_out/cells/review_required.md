# Human Review Artifact

Overall validation status: **REVIEW_REQUIRED**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

### u00 — Cell
- Source span: "All living things are made of very small parts called cells. A cell is the basic unit of every living organism. Some living things, like bacteria, are made of only one cell. Other living things, like plants, animals, and humans, are made of many millions of cells working together to form a body."
- Educational sentence: "Cells are the basic units of all living things, and some, like bacteria, have just one cell."
- Grounded (heuristic): True
- Semantic sign plan: ['CELLS', 'BASIC UNITS OF', 'LIVING THINGS', 'SOME HAVE', 'ONE CELL', 'LIKE BACTERIA']

### u01 — Organelles
- Source span: "Inside a cell there are many different parts, and each part has its own job to do. These parts are called organelles. Just like the organs in your body each have a function — your heart pumps blood, your lungs help you breathe — the organelles inside a cell each perform a specific function that keeps the cell alive and working properly."
- Educational sentence: "Organelles are parts inside a cell that each have a specific job to keep the cell alive."
- Grounded (heuristic): True
- Semantic sign plan: ['ORGANELLES', 'PARTS', 'INSIDE', 'CELL', 'SPECIFIC JOB', 'KEEP ALIVE']

### u02 — Cells_in_Organisms
- Source span: "A living organism's whole body is built from cells. Groups of similar cells work together to form tissues, tissues form organs, and organs form body systems. This is true for both plants and animals — from the smallest insect to the largest tree, every part of a living organism's body is ultimately made of cells, each one small, each one containing the same basic organelles, each one doing its part to keep the whole organism alive."
- Educational sentence: "A living organism's body is made of cells that form tissues, organs, and body systems."
- Grounded (heuristic): True
- Semantic sign plan: ['ORGANISM', 'BODY', 'MADE OF', 'FORM', 'CELLS', 'TISSUES', 'ORGANS', 'BODY SYSTEMS']

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).

- `u00` **CELLS** — ⚠️ REVIEW REQUIRED
  - reason: no verified lexical sign, and Arabic terminology translation was not usable
- `u00` **BASIC UNITS OF** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BASIC UNITS OF' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'الوحدات الأساسية' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **LIVING THINGS** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'LIVING THINGS' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أحياء' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **SOME HAVE** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'SOME HAVE' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'بعض' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **ONE CELL** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'ONE CELL' (Falcon selected candidate 'One' (id=5505e919-e090-466e-bd44-bdb2ac2bd282) but it was rejected by the information-loss safeguard (ESSENTIAL_INFORMATION_LOSS): the query 'ONE CELL' has a semantic head/content token this candidate does not represent - a false lexical sign is worse than honest fingerspelling); fingerspelled Arabic term 'الخلية' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **LIKE BACTERIA** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected candidate 'Bacteria' from 1 retrieved candidates (id=07d2c108-f363-40a5-af91-3531772ef6da); reason: The semantic item 'LIKE BACTERIA' refers to bacteria, which matches the candidate's English label 'Bacteria'.; verified id is in candidate set, has video, information_loss=FULL
- `u01` **ORGANELLES** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'ORGANELLES' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أُعضاء الخلية' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **PARTS** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'PARTS' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أجزاء' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **INSIDE** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='INSIDE' == catalog word_en/word_ar='Inside' / 'داخل'
- `u01` **CELL** — ⚠️ REVIEW REQUIRED
  - reason: no verified lexical sign, and Arabic terminology translation was not usable
- `u01` **SPECIFIC JOB** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'SPECIFIC JOB' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'وظيفة محددة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **KEEP ALIVE** — ⚠️ REVIEW REQUIRED
  - reason: no verified lexical sign, and Arabic terminology translation was not usable
- `u02` **ORGANISM** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'ORGANISM' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'كائن حي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **BODY** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BODY' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'الجسم' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **MADE OF** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'MADE OF' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'يتكوّن من' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **FORM** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'FORM' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تشكل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **CELLS** — ⚠️ REVIEW REQUIRED
  - reason: no verified lexical sign, and Arabic terminology translation was not usable
- `u02` **TISSUES** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'TISSUES' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أنسجة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **ORGANS** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'ORGANS' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أعضاء' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **BODY SYSTEMS** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BODY SYSTEMS' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أنظمة الجسم' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)

## Coverage summary

```json
{
  "total_sign_units": 6,
  "verified_signs": 1,
  "verified_signs_full": 1,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {
    "CANDIDATE_SELECTED": 1
  },
  "fallback_candidates": 4,
  "unsupported_units": 0,
  "review_required_units": 1,
  "full_verified_lexical_coverage_pct": 16.7,
  "verified_lexical_sign_coverage_pct": 16.7,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 83.3,
  "verified_signs_zho": 1,
  "verified_signs_esl_zayed_supplementary": 0,
  "institutional_zho_coverage_pct": 16.7,
  "supplementary_observed_emirati_coverage_pct": 0.0,
  "combined_known_source_lexical_coverage_pct": 16.7,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```

## Review reasons

- u00: 'CELLS' REVIEW_REQUIRED — no verified lexical sign, and Arabic terminology translation was not usable
- u00: unit-level review_required flag set
