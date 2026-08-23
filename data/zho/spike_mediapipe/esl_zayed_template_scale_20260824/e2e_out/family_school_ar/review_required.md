# Human Review Artifact

Overall validation status: **REVIEW_REQUIRED**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

### u00 — عائلة
- Source span: "أبي طبيب وأمي معلمة. لدي أخ واحد وأخت واحدة. كل صباح نمشي إلى المدرسة معًا."
- Educational sentence: "أبي طبيب وأمي معلمة، لدي أخ واحد وأخت واحدة، ونذهب جميعًا إلى مدرستي كل صباح."
- Grounded (heuristic): True
- Semantic sign plan: ['أبُ', 'طبيب', 'أمُ', 'معلمة', 'إخٌ', 'أخته', 'نمشي', 'إلى', 'مدرستي', 'كل', 'صباح']

### u01 — مدرسة
- Source span: "في المدرسة تعطينا المعلمة كتابًا جديدًا لنقرأه."
- Educational sentence: "في المدرسة تعطينا المعلمة كتابًا جديدًا لنقرأه."
- Grounded (heuristic): True
- Semantic sign plan: ['مدرسة', 'تعطي', 'المعلمة', 'كتاب', 'نريد', 'قراءة']

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).

- `u00` **أبُ** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'أبُ' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أبُ' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **طبيب** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='طبيب' == catalog word_en/word_ar='Doctor' / 'طبيب'
- `u00` **أمُ** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'أمُ' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أمُ' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **معلمة** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'معلمة' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'معلمة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **إخٌ** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'إخٌ' (Falcon selected id=null which was NOT in the candidate set - rejected outright (possible hallucination)); fingerspelled Arabic term 'إخٌ' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **أخته** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'أخته' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أخته' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **نمشي** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'نمشي' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'نمشي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **إلى** — ❌ UNSUPPORTED
  - reason: no verified lexical sign, and fingerspelling 'إلى' left unresolved letters ['ى']
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **مدرستي** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'مدرستي' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'مدرستي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **كل** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'كل' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'كل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **صباح** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='صباح' == catalog word_en/word_ar='Morning' / 'صباح'
- `u01` **مدرسة** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='مدرسة' == catalog word_en/word_ar='School' / 'مدرسة'
- `u01` **تعطي** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'تعطي' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تعطي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **المعلمة** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'المعلمة' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'المعلمة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **كتاب** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='كتاب' == catalog word_en/word_ar='Book' / 'كتاب'
- `u01` **نريد** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'نريد' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'نريد' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **قراءة** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='قراءة' == supplementary english_meaning/arabic_text='Read' / 'قراءة' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)

## Coverage summary

```json
{
  "total_sign_units": 11,
  "verified_signs": 2,
  "verified_signs_full": 2,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {
    "EXACT_AR": 2
  },
  "fallback_candidates": 8,
  "unsupported_units": 1,
  "review_required_units": 0,
  "full_verified_lexical_coverage_pct": 18.2,
  "verified_lexical_sign_coverage_pct": 18.2,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 90.9,
  "verified_signs_zho": 2,
  "verified_signs_esl_zayed_supplementary": 0,
  "institutional_zho_coverage_pct": 18.2,
  "supplementary_observed_emirati_coverage_pct": 0.0,
  "combined_known_source_lexical_coverage_pct": 18.2,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```

## Review reasons

- u00: 'إلى' UNSUPPORTED — no verified lexical sign, and fingerspelling 'إلى' left unresolved letters ['ى']
- u00: unit-level review_required flag set
