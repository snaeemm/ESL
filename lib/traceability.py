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

        render_source = resolution.get("render_source")
        catalog_ref = resolution.get("catalog_ref")
        supplementary_ref = resolution.get("supplementary_ref")
        arabic_caption_source = seg.get("arabic_caption_source")
        if render_source == "ZHO" and catalog_ref:
            selected_asset = {"zho_stable_id": catalog_ref.get("id"), "word_en": catalog_ref.get("word_en"),
                               "word_ar": catalog_ref.get("word_ar")}
            if arabic_caption_source == "ESL_ZAYED_FALLBACK":
                # Bug #1 fix: ZHO's own word_ar was missing/corrupt
                # (word_ar_integrity != VALID) so the rendered Arabic
                # caption actually came from the ESL Zayed supplementary
                # catalog for the same concept -- surfaced explicitly here
                # so traceability/UI never implies ZHO-institutional
                # authority for this caption.
                selected_asset["arabic_caption_source"] = "ESL_ZAYED_FALLBACK"
                selected_asset["arabic_fallback_supplementary_id"] = seg.get("arabic_fallback_supplementary_id")
                selected_asset["arabic_fallback_text"] = seg.get("arabic_fallback_text")
        elif render_source == "ESL_ZAYED" and supplementary_ref:
            selected_asset = {"supplementary_id": supplementary_ref.get("supplementary_id"),
                               "youtube_video_id": supplementary_ref.get("youtube_video_id"),
                               "segment_start_s": supplementary_ref.get("segment_start_s"),
                               "segment_end_s": supplementary_ref.get("segment_end_s"),
                               "arabic_text": supplementary_ref.get("arabic_text"),
                               "english_meaning": supplementary_ref.get("english_meaning")}
        elif render_source == "FINGERSPELL":
            selected_asset = {"fingerspell": resolution.get("fingerspell")}
        else:
            selected_asset = None

        rows.append({
            "segment_stem": seg["stem"],
            "sign_decision": {
                "term": resolution.get("term"),
                "status": resolution.get("status"),
                "match_method": resolution.get("match_method"),
                "fallback_type": resolution.get("fallback_type"),
                "catalog_ref": catalog_ref,
                "supplementary_ref": supplementary_ref,
                "fingerspell": resolution.get("fingerspell"),
                "match_reason": resolution.get("match_reason"),
                "retrieval_trace": resolution.get("retrieval_trace"),
            },
            # Provenance/traceability fields required for every rendered
            # semantic item (brief §6): ZHO carries zho_stable_id under
            # selected_asset; ESL Zayed carries youtube_video_id/segment
            # boundaries/arabic_text/english_meaning under selected_asset;
            # fingerspelling carries source_authority=NONE and an explicit
            # gap_reason. supporting_sources holds evidence from the OTHER
            # source when both exist for the same concept but only one was
            # actually selected/rendered - never implies the asset "came
            # from both".
            "semantic_concept": unit.get("concept"),
            "source_span": unit.get("source_span"),
            "render_source": render_source,
            "source_authority": resolution.get("source_authority"),
            "verification_status": ("SUPPLEMENTARY_UNVERIFIED" if render_source == "ESL_ZAYED"
                                     else "ZHO_INSTITUTIONAL_VERIFIED" if render_source == "ZHO"
                                     else "UNVERIFIED_FALLBACK" if render_source == "FINGERSPELL"
                                     else None),
            "supporting_sources": resolution.get("supporting_sources", []),
            "arabic_caption_source": arabic_caption_source or render_source,
            "selected_asset": selected_asset,
            "selection_reason": resolution.get("match_reason"),
            "gap_reason": resolution.get("gap_reason"),
            "semantic_sign_plan_item_index": idx,
            "unit_id": seg["unit_id"],
            "educational_sentence": unit.get("educational_sentence"),
            "concept": unit.get("concept"),
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
              "Every rendered segment below is traced back to the exact verified source span it came from. "
              "`render_source` distinguishes ZHO (institutional UAE sign reference) from ESL_ZAYED "
              "(observed, supplementary, NOT institutionally verified) and FINGERSPELL (no supported "
              "lexical sign found).", "",
              "| Segment | Sign decision | Render source | Match method | Term | Sign label (EN / AR) | Concept | Educational sentence | Source span |",
              "|---|---|---|---|---|---|---|---|---|"]
    for row in trace["segments"]:
        decision = row["sign_decision"]
        status = decision.get("status") or ""
        if decision.get("fallback_type"):
            status = f"{status} ({decision['fallback_type']})"
        ref = decision.get("catalog_ref") or decision.get("supplementary_ref") or {}
        if decision.get("catalog_ref"):
            asset = row.get("selected_asset") or {}
            if asset.get("arabic_caption_source") == "ESL_ZAYED_FALLBACK":
                label = f"{ref.get('word_en','')} / {asset.get('arabic_fallback_text','')} [ESL_ZAYED_FALLBACK]"
            else:
                label = f"{ref.get('word_en','')} / {ref.get('word_ar','')}"
        elif decision.get("supplementary_ref"):
            label = f"{ref.get('english_meaning','')} / {ref.get('arabic_text','')}"
        else:
            label = ""
        lines.append(
            f"| `{row['segment_stem']}` | {status} | {row.get('render_source') or ''} | {decision.get('match_method') or ''} | {decision.get('term','')} | "
            f"{label} | {row.get('concept','')} | {row.get('educational_sentence','')} | "
            f"\"{row.get('source_span','')}\" |"
        )
    lines.append("")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
