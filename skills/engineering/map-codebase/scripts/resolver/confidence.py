"""Deterministic confidence calibration from ownership evidence."""

from __future__ import annotations

import math
from typing import Any, Literal

from resolver.schemas import ConfidenceAssessment, ResolutionStatus


def assess_confidence(
    ranked: list[dict[str, Any]],
    *,
    freshness: str,
    focused: bool,
    underspecified: bool = False,
) -> ConfidenceAssessment:
    if underspecified or not ranked:
        reason = "task is underspecified" if underspecified else "no direct ownership evidence"
        return ConfidenceAssessment("abstain", 0.0, "low", (), (reason,))
    top = ranked[0]
    score = float(top.get("score", 0.0))
    margin = score - (float(ranked[1].get("score", 0.0)) if len(ranked) > 1 else 0.0)
    evidence = top.get("evidence", {})
    families = {
        family for weight, family in evidence.values()
        if weight > 0 and family not in {"import_relationship", "reverse_import_relationship", "related_test"}
    }
    exact_symbol = any(label.startswith("exact_symbol:") for label in evidence)
    exact_path = any(label.startswith("exact_path:") for label in evidence)
    filename = any(label.startswith("filename:") for label in evidence)
    component_match = bool(top.get("component_match"))
    subsystem_match = bool(top.get("subsystem_match"))
    conflicts = int(top.get("negative_conflicts", 0))
    raw = (
        -2.1
        + min(score, 60.0) / 18.0
        + min(margin, 20.0) / 12.0
        + min(len(families), 4) * 0.22
        + (0.9 if exact_symbol else 0.0)
        + (0.7 if exact_path else 0.0)
        + (0.35 if component_match else 0.0)
        + (0.25 if subsystem_match else 0.0)
        + (0.2 if focused else 0.0)
        - conflicts * 1.1
        - (0.8 if freshness != "fresh" else 0.0)
    )
    probability = round(1.0 / (1.0 + math.exp(-raw)), 4)
    unique_exact = (exact_symbol or exact_path) and conflicts == 0 and focused and freshness == "fresh"
    resolved = conflicts == 0 and (
        unique_exact
        or (probability >= 0.65 and margin >= 2 and len(families) >= 2)
        or (component_match and score >= 25 and margin >= 1)
    )
    ambiguous = score >= 8 and not resolved
    status: ResolutionStatus = "resolved" if resolved else "ambiguous" if ambiguous else "abstain"
    high = resolved and (
        unique_exact
        or (probability >= 0.90 and len(families) >= 3 and (component_match or subsystem_match))
    )
    level: Literal["high", "medium", "low"] = "high" if high else "medium" if status != "abstain" else "low"
    reasons = [
        f"top direct score {score:.3f}",
        f"candidate margin {margin:.3f}",
        f"{len(families)} direct evidence families",
    ]
    if exact_symbol:
        reasons.append("unique exact symbol evidence is confidence-eligible")
    uncertainties = []
    if margin < 4:
        uncertainties.append("candidate score separation is below the resolution margin")
    if len(families) < 2:
        uncertainties.append("fewer than two direct evidence families support ownership")
    if not (exact_symbol or exact_path or filename):
        uncertainties.append("no exact symbol, exact path, or filename evidence supports high confidence")
    if conflicts:
        uncertainties.append(f"{conflicts} negative query conflict(s) remain")
    if freshness != "fresh":
        uncertainties.append("knowledge is not fresh")
    return ConfidenceAssessment(
        status,
        probability,
        level,
        tuple(reasons),
        tuple(uncertainties),
        conflicts,
    )
