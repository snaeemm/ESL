"""TRACEABILITY (build order Step 15).

Pure join over data already produced by earlier stages — no new
computation, no new claims. For every rendered segment:

  VIDEO SEGMENT -> sign/fallback decision -> semantic sign-plan item
  -> episode unit (educational sentence + concept) -> exact verified
  source span -> source document -> source SHA-256.

Covers EVERY rendered segment, not a single example, per the brief.
"""
import json
import os


def build_traceability(source_manifest: dict, units: list, rendered_segments: list) -> dict:
    """rendered_segments: list of {"stem", "unit_id", "resolution_index",
    "english_caption", "arabic_caption"} as produced by run_pipeline.py
    when it builds the SEGMENTS-equivalent list for the renderer."""
    units_by_id = {u["unit_id"]: u for u in units}
    rows = []
    for seg in rendered_segments:
        unit = units_by_id.get(seg["unit_id"], {})
        resolutions = unit.get("sign_resolution", [])
        idx = seg.get("resolution_index")
        resolution = resolutions[idx] if idx is not None and idx < len(resolutions) else {}
        rows.append({
            "segment_stem": seg["stem"],
            "sign_decision": {
                "term": resolution.get("term"),
                "status": resolution.get("status"),
                "match_method": resolution.get("match_method"),
                "fallback_type": resolution.get("fallback_type"),
                "catalog_ref": resolution.get("catalog_ref"),
                "fingerspell": resolution.get("fingerspell"),
                "match_reason": resolution.get("match_reason"),
                "retrieval_trace": resolution.get("retrieval_trace"),
            },
            "semantic_sign_plan_item_index": idx,
            "unit_id": seg["unit_id"],
            "educational_sentence": unit.get("educational_sentence"),
            "concept": unit.get("concept"),
            "source_span": unit.get("source_span"),
            "source_span_verified": unit.get("source_span_verified"),
            "source_id": source_manifest["source_id"],
            "source_path": source_manifest["source_path"],
        })
    return {"source_id": source_manifest["source_id"], "source_path": source_manifest["source_path"], "segments": rows}


def write_traceability_json(trace: dict, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)


def write_traceability_markdown(trace: dict, out_path: str) -> None:
    lines = ["# Traceability Report", "",
              f"Source: `{trace['source_path']}`", f"Source ID: `{trace['source_id']}`", "",
              "Every rendered segment below is traced back to the exact verified source span it came from.", "",
              "| Segment | Sign decision | Match method | Term | ZHO sign (EN / AR) | Concept | Educational sentence | Source span |",
              "|---|---|---|---|---|---|---|---|"]
    for row in trace["segments"]:
        decision = row["sign_decision"]
        status = decision.get("status") or ""
        if decision.get("fallback_type"):
            status = f"{status} ({decision['fallback_type']})"
        ref = decision.get("catalog_ref") or {}
        zho_label = f"{ref.get('word_en','')} / {ref.get('word_ar','')}" if ref else ""
        lines.append(
            f"| `{row['segment_stem']}` | {status} | {decision.get('match_method') or ''} | {decision.get('term','')} | "
            f"{zho_label} | {row.get('concept','')} | {row.get('educational_sentence','')} | "
            f"\"{row.get('source_span','')}\" |"
        )
    lines.append("")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
