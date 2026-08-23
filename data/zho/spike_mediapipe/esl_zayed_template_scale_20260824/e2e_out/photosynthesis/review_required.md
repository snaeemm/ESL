# Human Review Artifact

Overall validation status: **PASS**

This prototype's developer is NOT a qualified Arabic Sign Language linguist. Nothing below — LLM output, dictionary matching, or successful rendering — should be treated as proof of linguistic correctness. Production deployment requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).

## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)
Reviewer: subject-matter teacher / curriculum reviewer.

## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)
Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).


## Coverage summary

```json
{
  "total_sign_units": 0,
  "verified_signs": 0,
  "verified_signs_full": 0,
  "verified_signs_partial_modifier_loss": 0,
  "verified_by_match_method": {},
  "fallback_candidates": 0,
  "unsupported_units": 0,
  "review_required_units": 0,
  "full_verified_lexical_coverage_pct": 0.0,
  "verified_lexical_sign_coverage_pct": 0.0,
  "partial_lexical_representation_pct": 0.0,
  "renderable_coverage_with_fallback_pct": 0.0,
  "verified_signs_zho": 0,
  "verified_signs_esl_zayed_supplementary": 0,
  "institutional_zho_coverage_pct": 0.0,
  "supplementary_observed_emirati_coverage_pct": 0.0,
  "combined_known_source_lexical_coverage_pct": 0.0,
  "_note": "full_verified_lexical_coverage_pct is the conservative headline number - only information_loss=FULL matches (exact/alias/safe-morphology, or a Falcon-selected candidate confirmed to represent the query's full semantic content). verified_lexical_sign_coverage_pct additionally includes CORE_WITH_MODIFIER_LOSS matches (e.g. 'VERY HOT'->'Hot' - core meaning kept, an intensity modifier lost); partial_lexical_representation_pct isolates just that subset so it is never silently folded into a 'full accuracy' claim. ESSENTIAL_INFORMATION_LOSS candidates (e.g. 'ONE BROTHER'->'One' - the semantic head dropped) and AMBIGUOUS candidates are REJECTED before verification and never appear here - they fall through to fingerspelling/review. renderable_coverage_with_fallback_pct counts fingerspelled items as renderable, NOT as validated sign-language accuracy. Fingerspelling is a fallback, not a verified lexical sign — see fallback_type on each resolution. verified_by_match_method distinguishes exact/morphology/alias/candidate-selected matches; CANDIDATE_SELECTED and MORPHOLOGY_CANDIDATE matches were chosen/confirmed by Falcon from deterministically retrieved candidates and passed deterministic verification (including the information-loss gate), but are still LLM-in-the-loop and warrant closer human review than EXACT_EN/EXACT_AR matches — see the recovered-match audit table. institutional_zho_coverage_pct counts ONLY render_source=ZHO matches (the institutional UAE sign reference). supplementary_observed_emirati_coverage_pct counts ONLY render_source=ESL_ZAYED matches (an observed, supplementary, NOT institutionally verified source - verification_status is always SUPPLEMENTARY_UNVERIFIED on every ESL Zayed row). combined_known_source_lexical_coverage_pct is their sum and is deliberately NOT called an 'accuracy' number. verified_signs_zho / verified_signs_esl_zayed_supplementary are the same split as raw counts - ESL Zayed is never folded into ZHO's own headline coverage number."
}
```
