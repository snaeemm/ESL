"""AUTOMATED VALIDATOR (build order Step 11) + human-review artifact
(build order Step 10).

Runs entirely deterministically over the already-produced episode +
sign-resolution data — no model calls here. This is the last gate before
any rendering: BLOCKED prevents run_pipeline.py from proceeding to
CLIP PREP / MEDIAPIPE / RENDER at all.

Note on scope: this validator checks structural/provenance integrity
(does every claim point to something real) — it does NOT and cannot
validate linguistic correctness of the resulting sign sequence. That
distinction is exactly why the human-review artifact below exists and is
explicit about ACADEMIC review vs SIGN-LANGUAGE review being different
questions (see build order Step 10).
"""
import json
import os

from lib.sign_resolver import (
    STATUS_VERIFIED, STATUS_FINGERSPELL, STATUS_UNSUPPORTED, STATUS_REVIEW, coverage_report,
)

STATUS_PASS = "PASS"
STATUS_PASS_WITH_FALLBACK = "PASS_WITH_FALLBACK"
STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
STATUS_BLOCKED = "BLOCKED"


def validate_episode(units: list, source_text: str) -> dict:
    checks = {"source_grounding": {"total_units": 0, "verified_spans": 0, "failed": []},
              "sign_provenance": {"verified_signs": 0, "fingerspelled": 0, "unsupported": 0, "review_required": 0},
              "coverage": {}}

    blocking = []
    review_reasons = []
    any_fallback = False

    for u in units:
        checks["source_grounding"]["total_units"] += 1
        # Source grounding: every unit's own claimed span must actually
        # occur in the real source text (re-checked here, not just trusted
        # from upstream — this is the validator's own independent gate).
        span_ok = bool(u.get("source_span")) and u["source_span"] in source_text
        if span_ok:
            checks["source_grounding"]["verified_spans"] += 1
        else:
            checks["source_grounding"]["failed"].append(u.get("unit_id"))
            blocking.append(f"{u.get('unit_id')}: source_span not found verbatim in source text")

        # Educational provenance: no unit without a concept + span.
        if not u.get("concept") or not u.get("source_span"):
            blocking.append(f"{u.get('unit_id')}: missing concept or source_span (no provenance)")

        for r in u.get("sign_resolution", []):
            if r["status"] == STATUS_VERIFIED:
                checks["sign_provenance"]["verified_signs"] += 1
                ref = r.get("catalog_ref") or {}
                if not ref.get("id"):
                    blocking.append(f"{u.get('unit_id')}: VERIFIED_SIGN '{r['term']}' has no catalog_ref id")
            elif r["status"] == STATUS_FINGERSPELL:
                checks["sign_provenance"]["fingerspelled"] += 1
                any_fallback = True
                fs = r.get("fingerspell") or {}
                if not fs.get("fully_resolved"):
                    blocking.append(f"{u.get('unit_id')}: FINGERSPELL_CANDIDATE '{r['term']}' is not fully resolved to catalog letters")
            elif r["status"] == STATUS_UNSUPPORTED:
                checks["sign_provenance"]["unsupported"] += 1
                review_reasons.append(f"{u.get('unit_id')}: '{r['term']}' UNSUPPORTED — {r.get('match_reason', '')}")
            elif r["status"] == STATUS_REVIEW:
                checks["sign_provenance"]["review_required"] += 1
                review_reasons.append(f"{u.get('unit_id')}: '{r['term']}' REVIEW_REQUIRED — {r.get('match_reason', '')}")

        if u.get("review_required"):
            review_reasons.append(f"{u.get('unit_id')}: unit-level review_required flag set")

    checks["coverage"] = coverage_report(units)

    if blocking:
        overall = STATUS_BLOCKED
    elif review_reasons:
        overall = STATUS_REVIEW_REQUIRED
    elif any_fallback:
        overall = STATUS_PASS_WITH_FALLBACK
    else:
        overall = STATUS_PASS

    return {
        "overall_status": overall,
        "checks": checks,
        "blocking_conditions_hit": blocking,
        "review_reasons": review_reasons,
    }


def can_render(validation: dict, allow_review_render: bool) -> bool:
    """Rendering proceeds on PASS / PASS_WITH_FALLBACK always. On
    REVIEW_REQUIRED, only if the caller explicitly passed
    --allow-review-render (producing a clearly marked PROTOTYPE/PENDING
    REVIEW artifact per Step 11) — never silently upgraded to validated.
    BLOCKED never renders, regardless of the flag."""
    status = validation["overall_status"]
    if status == STATUS_BLOCKED:
        return False
    if status == STATUS_REVIEW_REQUIRED:
        return allow_review_render
    return True


def write_review_markdown(units: list, validation: dict, out_path: str) -> None:
    """Human-review artifact per Step 10 — no UI, just a reviewer-friendly
    Markdown, split into ACADEMIC REVIEW (does the episode preserve
    curriculum meaning?) and SIGN-LANGUAGE REVIEW (is the signed
    representation linguistically appropriate?) as two distinct
    questions, since they need different reviewers."""
    lines = ["# Human Review Artifact", "",
              f"Overall validation status: **{validation['overall_status']}**", "",
              "This prototype's developer is NOT a qualified Arabic Sign Language linguist. "
              "Nothing below — LLM output, dictionary matching, or successful rendering — "
              "should be treated as proof of linguistic correctness. Production deployment "
              "requires a qualified UAE/Arabic Sign Language expert checkpoint (see README).",
              "",
              "## ACADEMIC REVIEW (does the episode preserve curriculum meaning?)",
              "Reviewer: subject-matter teacher / curriculum reviewer.", ""]

    for u in units:
        lines.append(f"### {u.get('unit_id')} — {u.get('concept')}")
        lines.append(f"- Source span: \"{u.get('source_span', '')}\"")
        lines.append(f"- Educational sentence: \"{u.get('educational_sentence', '')}\"")
        lines.append(f"- Grounded (heuristic): {u.get('educational_sentence_grounded', 'n/a')}")
        lines.append(f"- Semantic sign plan: {u.get('semantic_sign_plan', [])}")
        lines.append("")

    lines += ["## SIGN-LANGUAGE REVIEW (is the signed representation linguistically appropriate?)",
              "Reviewer: qualified UAE/Arabic Sign Language expert (not available for this prototype — flagged, not simulated).", ""]

    for u in units:
        for r in u.get("sign_resolution", []):
            marker = {"VERIFIED_SIGN": "✅ VERIFIED UAE/ZHO sign",
                      "FINGERSPELL_CANDIDATE": "🔤 Arabic fingerspelling fallback",
                      "UNSUPPORTED": "❌ UNSUPPORTED",
                      "REVIEW_REQUIRED": "⚠️ REVIEW REQUIRED"}.get(r["status"], r["status"])
            lines.append(f"- `{u.get('unit_id')}` **{r['term']}** — {marker}")
            lines.append(f"  - reason: {r.get('match_reason', '')}")
            if r.get("fallback_type"):
                lines.append(f"  - fallback_type: {r['fallback_type']} (NOT equivalent to a verified lexical sign)")
    lines.append("")

    lines += ["## Coverage summary", "", "```json",
              json.dumps(validation["checks"]["coverage"], indent=2, ensure_ascii=False),
              "```", ""]

    if validation["blocking_conditions_hit"]:
        lines += ["## Blocking conditions", ""] + [f"- {b}" for b in validation["blocking_conditions_hit"]] + [""]
    if validation["review_reasons"]:
        lines += ["## Review reasons", ""] + [f"- {r}" for r in validation["review_reasons"]] + [""]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
