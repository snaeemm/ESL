# Human Review Artifact

Overall validation status: **REVIEW_REQUIRED**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

### u00 — مدرس
- Source span: "يبه دكتور وأمي معلمة بالمدرسة."
- Educational sentence: "دكتور هو مدرس."
- Grounded (heuristic): True
- Semantic sign plan: ['دكتور', 'هو', 'معلم']

### u03 — جو الصيف
- Source span: "وحار وايد بالصيف."
- Educational sentence: ""
- Grounded (heuristic): False
- Semantic sign plan: []

### u01 — معلمة
- Source span: "يبه دكتور وأمي معلمة بالمدرسة."
- Educational sentence: "أمي هي معلمة في المدرسة."
- Grounded (heuristic): True
- Semantic sign plan: ['أم', 'هي', 'معلمة', 'في', 'المدرسة']

### u02 — ذهاب للمدرسة
- Source span: "احنا نروح المدرسة كل يوم الصبح."
- Educational sentence: "نحن نذهب للمدرسة كل صباح."
- Grounded (heuristic): True
- Semantic sign plan: ['نعيش', 'نفعل', 'ذهاب', 'للسَّماء', 'كل', 'صباح']

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).

- `u00` **دكتور** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'دكتور' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'دكتور' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **هو** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='هو' == supplementary english_meaning/arabic_text='He' / 'هو' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u00` **معلم** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='معلم' == catalog word_en/word_ar='Teacher' / 'معلم'
- `u01` **أم** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'أم' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أم' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **هي** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'هي' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'هي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **معلمة** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'معلمة' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'معلمة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **في** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'في' (Falcon reviewed 1 candidates and answered NONE: None of the candidates match the semantic item 'في' in the context of indicating location or state, as they relate to official documents.); fingerspelled Arabic term 'في' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **المدرسة** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'المدرسة' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'المدرسة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **نعيش** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'نعيش' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'نعيش' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **نفعل** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'نفعل' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'نفعل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **ذهاب** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'ذهاب' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'ذهاب' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **للسَّماء** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'للسَّماء' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'للسَّماء' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **كل** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'كل' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'كل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **صباح** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='صباح' == catalog word_en/word_ar='Morning' / 'صباح'

## Coverage summary

```json
{
  "total_sign_units": 3,
  "verified_signs": 2,
  "verified_signs_full": 2,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {
    "ESL_ZAYED_EXACT": 1,
    "EXACT_AR": 1
  },
  "fallback_candidates": 1,
  "unsupported_units": 0,
  "review_required_units": 0,
  "full_verified_lexical_coverage_pct": 66.7,
  "verified_lexical_sign_coverage_pct": 66.7,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 100.0,
  "verified_signs_zho": 1,
  "verified_signs_esl_zayed_supplementary": 1,
  "institutional_zho_coverage_pct": 33.3,
  "supplementary_observed_emirati_coverage_pct": 33.3,
  "combined_known_source_lexical_coverage_pct": 66.7,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```

## Review reasons

- u03: unit-level review_required flag set
