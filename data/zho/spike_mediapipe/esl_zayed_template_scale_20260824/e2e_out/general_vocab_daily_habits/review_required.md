# Human Review Artifact

Overall validation status: **PASS_WITH_FALLBACK**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

### u00 — Morning Routine
- Source span: "A clever student uses a clear routine: wake up, read a book, and eat breakfast before school starts."
- Educational sentence: "A clever student wakes up, reads a book, and eats breakfast before school starts."
- Grounded (heuristic): True
- Semantic sign plan: ['STUDENT', 'WAKE UP', 'READ', 'BOOK', 'EAT', 'BREAKFAST', 'BEFORE', 'SCHOOL STARTS']

### u01 — Patience
- Source span: "A polite and patient student does not get bored during a difficult lesson. They stay active and quiet, listen carefully, and try not to forget what they have learned."
- Educational sentence: "A polite and patient student stays active, listens carefully, and doesn't get bored during a difficult lesson."
- Grounded (heuristic): True
- Semantic sign plan: ['POLITE', 'STUDENT', 'STAY ACTIVE', 'LISTEN CAREFULLY', 'DO NOT GET BORED', 'DIFFICULT LESSON']

### u02 — Focus
- Source span: "If a student loses focus, they should not lose hope, with practice, even a difficult subject becomes easy."
- Educational sentence: "If a student loses focus, they should not lose hope, and with practice, even a difficult subject becomes easy."
- Grounded (heuristic): True
- Semantic sign plan: ['LOSE', 'FOCUS', 'LOOSE', 'HOPE', 'PRACTICE', 'DIFFICULT', 'BECOME', 'EASY']

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).

- `u00` **STUDENT** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'STUDENT' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'طالب ذكي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **WAKE UP** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected candidate 'wakes up' from 1 retrieved candidates (id=97fe13f3-9d7b-4e12-9a44-4ae5617edf66); reason: The candidate 'wakes up' directly matches the semantic item 'WAKE UP' in the given context.; verified id is in candidate set, has video, information_loss=FULL
- `u00` **READ** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='READ' == supplementary english_meaning/arabic_text='Read' / 'قراءة' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u00` **BOOK** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='BOOK' == catalog word_en/word_ar='Book' / 'كتاب'
- `u00` **EAT** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='EAT' == supplementary english_meaning/arabic_text='Eat' / 'أكل' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u00` **BREAKFAST** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BREAKFAST' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'الإفطار' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **BEFORE** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='BEFORE' == catalog word_en/word_ar='Before' / 'أمام'
- `u00` **SCHOOL STARTS** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected candidate 'School' from 4 retrieved candidates (id=2499aa36-8999-46df-b950-963d38e85700); reason: The semantic item 'SCHOOL STARTS' refers to the concept of school in general, making 'School' the most appropriate match.; verified id is in candidate set, has video, information_loss=FULL
- `u01` **POLITE** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='POLITE' == supplementary english_meaning/arabic_text='Polite' / 'مؤدب' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u01` **STUDENT** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'STUDENT' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'طالب' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **STAY ACTIVE** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected ESL Zayed candidate 'Active' from 1 retrieved candidates (id=ESL_ZAYED_0097); reason: The candidate 'Active' directly matches the semantic item 'STAY ACTIVE' in the context.; verified id is in candidate set, content_type=WORD, source segment/video metadata complete, information_loss=FULL; source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE
- `u01` **LISTEN CAREFULLY** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'LISTEN CAREFULLY' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'يزيد الانتباه' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **DO NOT GET BORED** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected ESL Zayed candidate 'Bored' from 1 retrieved candidates (id=ESL_ZAYED_0086); reason: The candidate directly matches the semantic item 'DO NOT GET BORED' with the word 'Bored' in English.; verified id is in candidate set, content_type=WORD, source segment/video metadata complete, information_loss=CORE_WITH_MODIFIER_LOSS; source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE
- `u01` **DIFFICULT LESSON** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected candidate 'Difficult' from 1 retrieved candidates (id=abd40727-b79c-40e3-8228-ecf7a904044c); reason: The semantic item 'DIFFICULT LESSON' matches the candidate's meaning of 'Difficult' in the context of a lesson.; verified id is in candidate set, has video, information_loss=FULL
- `u02` **LOSE** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='LOSE' == supplementary english_meaning/arabic_text='Lose' / 'ضاع' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u02` **FOCUS** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'FOCUS' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تفرغ' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **LOOSE** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'LOOSE' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'يتراجع' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **HOPE** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'HOPE' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أمل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **PRACTICE** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'PRACTICE' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تمرين' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **DIFFICULT** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='DIFFICULT' == catalog word_en/word_ar='Difficult' / 'صعب'
- `u02` **BECOME** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BECOME' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'يَصِبُ' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **EASY** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='EASY' == catalog word_en/word_ar='Easy' / 'سهل'

## Coverage summary

```json
{
  "total_sign_units": 8,
  "verified_signs": 6,
  "verified_signs_full": 6,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {
    "CANDIDATE_SELECTED": 2,
    "ESL_ZAYED_EXACT": 2,
    "EXACT_EN": 2
  },
  "fallback_candidates": 2,
  "unsupported_units": 0,
  "review_required_units": 0,
  "full_verified_lexical_coverage_pct": 75.0,
  "verified_lexical_sign_coverage_pct": 75.0,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 100.0,
  "verified_signs_zho": 4,
  "verified_signs_esl_zayed_supplementary": 2,
  "institutional_zho_coverage_pct": 50.0,
  "supplementary_observed_emirati_coverage_pct": 25.0,
  "combined_known_source_lexical_coverage_pct": 75.0,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```
