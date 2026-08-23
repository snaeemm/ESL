# Human Review Artifact

Overall validation status: **PASS_WITH_FALLBACK**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

### u00 — Community Helping
- Source span: "being helpful and active in the community is something we are taught from a young age."
- Educational sentence: "Being helpful and active in the community is something we learn from a young age."
- Grounded (heuristic): True
- Semantic sign plan: ['LEARN', 'YOUNG AGE', 'BE HELPFUL', 'ACTIVE', 'COMMUNITY']

### u01 — Family Bonding
- Source span: "My brother bought chocolate and cake for a birthday celebration."
- Educational sentence: "My brother bought chocolate and cake for a family birthday celebration."
- Grounded (heuristic): True
- Semantic sign plan: ['BROTHER', 'BOUGHT', 'CHOCOLATE', 'CAKE', 'FAMILY', 'BIRTHDAY CELEBRATION']

### u02 — Cultural Appreciation
- Source span: "My sister wanted to visit the perfume and oud shop, because she loves the smell of incense and oud wood."
- Educational sentence: "My sister loves the smell of incense and oud wood, so she wanted to visit the perfume and oud shop."
- Grounded (heuristic): True
- Semantic sign plan: ['MY', 'SISTER', 'LOVE', 'SMELL', 'INCENSE', 'OUD', 'WOOD', 'WANT', 'VISIT', 'PERFUME', 'OUD', 'SHOP']

### u03 — Gratitude and Rewards
- Source span: "my father gave everyone a small gift as an award for a fun day out."
- Educational sentence: "My father gave everyone a small gift as an award for having a fun day out."
- Grounded (heuristic): True
- Semantic sign plan: ['FATHER', 'GIVE', 'SMALL GIFT', 'AWARD', 'HAVE FUN', 'DAY OUT']

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).

- `u00` **LEARN** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'LEARN' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تعلم' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **YOUNG AGE** — ✅ VERIFIED UAE/ZHO sign
  - reason: Falcon selected candidate 'Age' from 1 retrieved candidates (id=26c00e7d-e19b-4091-869b-042bacc51ab5); reason: The semantic item 'YOUNG AGE' is best represented by the candidate 'Age' as it directly refers to the concept of age, which is relevant in this context.; verified id is in candidate set, has video, information_loss=FULL
- `u00` **BE HELPFUL** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BE HELPFUL' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'مفيد' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u00` **ACTIVE** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='ACTIVE' == supplementary english_meaning/arabic_text='Active' / 'نشيط' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u00` **COMMUNITY** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'COMMUNITY' (Falcon selected id=null which was NOT in the candidate set - rejected outright (possible hallucination)); fingerspelled Arabic term 'المجتمع' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **BROTHER** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='BROTHER' == supplementary english_meaning/arabic_text='Brother' / 'أخي' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u01` **BOUGHT** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BOUGHT' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'اشتري' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u01` **CHOCOLATE** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='CHOCOLATE' == supplementary english_meaning/arabic_text='Chocolate' / 'حلاوه' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u01` **CAKE** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='CAKE' == supplementary english_meaning/arabic_text='Cake' / 'كيك' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u01` **FAMILY** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='FAMILY' == catalog word_en/word_ar='Family' / 'أسرة'
- `u01` **BIRTHDAY CELEBRATION** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'BIRTHDAY CELEBRATION' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'احتفال بعيد الميلاد' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **MY** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'MY' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'أنا' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **SISTER** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='SISTER' == catalog word_en/word_ar='Sister' / 'باب الأسرة'
- `u02` **LOVE** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'LOVE' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'حب' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **SMELL** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'SMELL' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'روائح' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **INCENSE** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='INCENSE' == supplementary english_meaning/arabic_text='Incense' / 'بخور' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u02` **OUD** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='OUD' == catalog word_en/word_ar='Oud' / 'عــود'
- `u02` **WOOD** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='WOOD' == catalog word_en/word_ar='Wood' / 'خشب'
- `u02` **WANT** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'WANT' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'تُفضِّل' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u02` **VISIT** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='VISIT' == supplementary english_meaning/arabic_text='Visit' / 'زيارة' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u02` **PERFUME** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='PERFUME' == catalog word_en/word_ar='Perfume' / 'مخمرية'
- `u02` **OUD** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='OUD' == catalog word_en/word_ar='Oud' / 'عــود'
- `u02` **SHOP** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'SHOP' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'متجر' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u03` **FATHER** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='FATHER' == catalog word_en/word_ar='Father' / 'باب الأسرة'
- `u03` **GIVE** — ✅ VERIFIED UAE/ZHO sign
  - reason: exact bilingual match: query='GIVE' == catalog word_en/word_ar='Give' / 'يعطي'
- `u03` **SMALL GIFT** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'SMALL GIFT' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'هدية صغيرة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u03` **AWARD** — ✅ VERIFIED UAE/ZHO sign
  - reason: ESL Zayed exact WORD-level match: query='AWARD' == supplementary english_meaning/arabic_text='Award' / 'جائزة' (source_authority=OBSERVED_EMIRATI_EDUCATIONAL_SOURCE, not institutional ZHO)
- `u03` **HAVE FUN** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'HAVE FUN' (no lexical (or embedding, if enabled) candidates found); fingerspelled Arabic term 'متعة' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)
- `u03` **DAY OUT** — 🔤 Arabic fingerspelling fallback
  - reason: no verified lexical sign for 'DAY OUT' (Falcon selected id=null which was NOT in the candidate set - rejected outright (possible hallucination)); fingerspelled Arabic term 'يوم ترفيهي' — all letters resolved against data/zho/arabic_alphabet_map.json
  - fallback_type: FINGERSPELL (NOT equivalent to a verified lexical sign)

## Coverage summary

```json
{
  "total_sign_units": 5,
  "verified_signs": 2,
  "verified_signs_full": 2,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {
    "CANDIDATE_SELECTED": 1,
    "ESL_ZAYED_EXACT": 1
  },
  "fallback_candidates": 3,
  "unsupported_units": 0,
  "review_required_units": 0,
  "full_verified_lexical_coverage_pct": 40.0,
  "verified_lexical_sign_coverage_pct": 40.0,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 100.0,
  "verified_signs_zho": 1,
  "verified_signs_esl_zayed_supplementary": 1,
  "institutional_zho_coverage_pct": 20.0,
  "supplementary_observed_emirati_coverage_pct": 20.0,
  "combined_known_source_lexical_coverage_pct": 40.0,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```
