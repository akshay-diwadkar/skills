"""Stage E: Confidence estimation engine."""

from __future__ import annotations

from typing import Any


def estimate_confidence(
    candidates: list[dict[str, Any]],
    signals: dict[str, Any],
    freshness_state: str = "fresh",
) -> tuple[str, list[str]]:
    """Estimate task resolution confidence level: 'high', 'medium', or 'low'."""
    reasons: list[str] = []

    if freshness_state != "fresh":
        reasons.append(f"Knowledge state is '{freshness_state}'; confidence capped.")
        return "low", reasons

    if not candidates:
        reasons.append("No candidates matched task signals.")
        return "low", reasons

    top_candidate = candidates[0]
    top_score = top_candidate["raw_score"]
    exact_matches = [c for c in candidates if c["exact_count"] > 0]

    # Score margin check
    second_score = candidates[1]["raw_score"] if len(candidates) > 1 else 0.0
    margin = top_score - second_score

    if exact_matches and (top_score >= 12.0 or margin >= 5.0):
        reasons.append("Exact symbol/path identifier matched with high evidence margin.")
        return "high", reasons
    elif top_score >= 7.0 or len(candidates) >= 2:
        reasons.append("Filename or subsystem signals agree across candidates.")
        return "medium", reasons
    else:
        reasons.append("Low evidence agreement across index candidates.")
        return "low", reasons
