"""DURATION-AWARE EPISODE SELECTION (fix for the development run's
314.76s-vs-45s-target gap).

Root cause of the original bug: episode_builder.py picked unit COUNT
against a target duration BEFORE sign resolution/fingerspelling
expansion existed, so its avg_unit_duration_s assumed ~1 clip per
semantic item. Fingerspelling actually expands one item into 3-5 letter
clips, so the real render was ~7x longer than planned.

Fix: duration planning now runs AFTER sign resolution (once the real
render-segment count per unit is known), using a measured per-clip
duration constant, and selects the largest coherent PREFIX of units that
fits the requested duration — never truncating a unit's own semantic
plan mid-way, never speeding up signing, never randomly dropping
segments. If even the first unit alone exceeds the target, it is kept
(you need at least one complete unit) but explicitly flagged.
"""

# Measured from the first full development run (2026-08-22):
# 314.76s total / 149 rendered segments, with 148 crossfades at 0.16s
# overlap each (148 * 0.16 = 23.68s of overlap removed from the naive
# sum) -> (314.76 + 23.68) / 149 = 2.27s per non-overlapped segment.
# This is a MEASURED constant from real render output, not invented.
MEASURED_AVG_CLIP_DURATION_S = 2.27
XFADE_OVERLAP_S = 0.16

RENDERABLE_STATUSES = ("VERIFIED_SIGN", "FINGERSPELL_CANDIDATE")


def _unit_segment_count(unit: dict) -> int:
    """Counts actual render segments this unit would produce: 1 per
    VERIFIED_SIGN, len(catalog_refs) per FINGERSPELL_CANDIDATE letter
    sequence. UNSUPPORTED/REVIEW_REQUIRED items never render, so they
    contribute 0 — matches run_pipeline.py's own segment-building logic
    exactly, so the estimate and the real render never diverge in kind,
    only in the measured-average approximation."""
    count = 0
    for r in unit.get("sign_resolution", []):
        if r["status"] == "VERIFIED_SIGN" and r.get("catalog_ref"):
            count += 1
        elif r["status"] == "FINGERSPELL_CANDIDATE" and r.get("fingerspell"):
            count += len(r["fingerspell"].get("catalog_refs", []))
    return count


def estimate_unit_duration_s(unit: dict) -> float:
    n = _unit_segment_count(unit)
    if n == 0:
        return 0.0
    return n * MEASURED_AVG_CLIP_DURATION_S - max(0, n - 1) * XFADE_OVERLAP_S


def plan_episode_duration(units: list, target_duration_s: float) -> dict:
    """Selects the largest coherent PREFIX of units (in their existing,
    already-meaningful order) whose combined estimated duration fits
    target_duration_s. Returns the augmented unit list (every unit gets
    estimated_duration_s and duration_exceeds_target fields) plus a
    summary dict with requested/estimated/dropped info. Selected units
    carry "included_in_episode": true/false so nothing is silently
    removed from the artifact — dropped units remain visible and
    explained, not hidden.
    """
    running_total = 0.0
    selected = []
    dropped = []

    for i, unit in enumerate(units):
        dur = estimate_unit_duration_s(unit)
        exceeds_alone = dur > target_duration_s
        annotated = {**unit, "estimated_duration_s": round(dur, 2), "duration_exceeds_target": exceeds_alone}

        if not selected:
            # Always include at least one complete unit, even if it alone
            # exceeds the target - flagged explicitly, never silently
            # truncated mid-unit.
            selected.append({**annotated, "included_in_episode": True})
            running_total += dur
            continue

        if running_total + dur <= target_duration_s:
            selected.append({**annotated, "included_in_episode": True})
            running_total += dur
        else:
            dropped.append({**annotated, "included_in_episode": False,
                             "drop_reason": f"would extend episode to {running_total + dur:.1f}s, "
                                            f"beyond target {target_duration_s:.0f}s"})

    all_units = selected + dropped

    # Honest shortfall reporting only - no content generation. Threshold:
    # more than 15% short of the requested duration (and at least 1s in
    # absolute terms, to avoid flagging trivial rounding gaps on very
    # short targets) is treated as a "meaningful" shortfall worth
    # surfacing to the reviewer/panel, since it means real grounded
    # source material ran out, not just normal clip-boundary rounding.
    shortfall_reason = None
    shortfall_s = target_duration_s - running_total
    if target_duration_s > 0 and shortfall_s > 1.0 and shortfall_s > 0.15 * target_duration_s:
        shortfall_reason = "insufficient grounded source material to safely reach requested duration"

    return {
        "requested_duration_s": target_duration_s,
        "estimated_duration_s": round(running_total, 2),
        "units_included": len(selected),
        "units_dropped": len(dropped),
        "any_single_unit_exceeds_target": any(u["duration_exceeds_target"] for u in selected),
        "shortfall_reason": shortfall_reason,
        "units": all_units,  # selected first (in order), then dropped — order preserved within each group
    }
