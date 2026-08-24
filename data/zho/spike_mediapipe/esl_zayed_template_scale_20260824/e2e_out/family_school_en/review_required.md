# Human Review Artifact

Overall validation status: **PASS_WITH_FALLBACK**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

### u00 — Family
- Source span: "My father is a doctor and my mother is a teacher. I have one brother and one sister."
- Educational sentence: "A family includes a father who is a doctor, a mother who is a teacher, a brother, and a sister."
- Grounded (heuristic): True
- Semantic sign plan: ['FAMILY', 'INCLUDE', 'FATHER', 'DOCTOR', 'MOTHER', 'TEACHER', 'BROTHER', 'SISTER']

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).

- `u00` **FAMILY** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='FAMILY' == catalog word_en/word_ar='Family' / 'أسرة'
- `u00` **INCLUDE** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'INCLUDE' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تُشكِّل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **FATHER** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='FATHER' == catalog word_en/word_ar='Father' / 'باب الأسرة'
- `u00` **DOCTOR** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='DOCTOR' == catalog word_en/word_ar='Doctor' / 'طبيب'
- `u00` **MOTHER** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='MOTHER' == catalog word_en/word_ar='Mother' / 'باب الأسرة'
- `u00` **TEACHER** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='TEACHER' == catalog word_en/word_ar='Teacher' / 'معلم'
- `u00` **BROTHER** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='BROTHER' == supplementary english_meaning/arabic_text='Brother' / 'أخي' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u00` **SISTER** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='SISTER' == catalog word_en/word_ar='Sister' / 'باب الأسرة'

## Coverage summary

```json
{
  "total_sign_units": 8,
  "verified_signs": 7,
  "verified_signs_full": 7,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {
    "EXACT_EN": 6,
    "ESL_ZAYED_EXACT": 1
  },
  "fallback_candidates": 1,
  "unsupported_units": 0,
  "review_required_units": 0,
  "full_verified_lexical_coverage_pct": 87.5,
  "verified_lexical_sign_coverage_pct": 87.5,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 100.0,
  "verified_signs_zho": 6,
  "verified_signs_esl_zayed_supplementary": 1,
  "institutional_zho_coverage_pct": 75.0,
  "supplementary_observed_emirati_coverage_pct": 12.5,
  "combined_known_source_lexical_coverage_pct": 87.5,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```
