from __future__ import annotations

from collections.abc import Mapping
from typing import Any

BALANCED_THRESHOLDS = {
    "hit_at_1": 0.85,
    "hit_at_3": 0.95,
    "mrr": 0.90,
    "primary_owner_precision": 0.85,
    "primary_owner_recall": 0.80,
    "exact_owner_set_match": 0.80,
    "false_primary_rate": 0.10,
    "constraint_precision": 0.75,
    "constraint_recall": 0.65,
    "impact_precision": 0.70,
    "impact_recall": 0.60,
    "abstention_precision": 0.90,
    "abstention_recall": 0.90,
}


def _phase1_gates(metrics: Mapping[str, Any], *, prefix: str = "") -> dict[str, bool]:
    return {
        f"{prefix}hit_at_1": metrics["hit_at_1"] >= BALANCED_THRESHOLDS["hit_at_1"],
        f"{prefix}hit_at_3": metrics["hit_at_3"] >= BALANCED_THRESHOLDS["hit_at_3"],
        f"{prefix}mrr": metrics["mrr"] >= BALANCED_THRESHOLDS["mrr"],
        f"{prefix}primary_owner_precision": metrics["primary_owner_precision"]
        >= BALANCED_THRESHOLDS["primary_owner_precision"],
        f"{prefix}primary_owner_recall": metrics["primary_owner_recall"]
        >= BALANCED_THRESHOLDS["primary_owner_recall"],
        f"{prefix}exact_owner_set_match": metrics["exact_owner_set_match"]
        >= BALANCED_THRESHOLDS["exact_owner_set_match"],
        f"{prefix}false_primary_rate": metrics["false_primary_rate"]
        <= BALANCED_THRESHOLDS["false_primary_rate"],
        f"{prefix}abstention_precision": metrics["abstention_precision"]
        >= BALANCED_THRESHOLDS["abstention_precision"],
        f"{prefix}abstention_recall": metrics["abstention_recall"]
        >= BALANCED_THRESHOLDS["abstention_recall"],
        f"{prefix}confidence_safety": metrics["incorrect_high_confidence"] == 0,
    }


def evaluate_balanced_gates(
    metrics: Mapping[str, Any],
    *,
    heldout: Mapping[str, Any] | None = None,
) -> dict[str, bool]:
    gates = _phase1_gates(metrics["phase1"])
    gates.update(
        {
            "constraint_precision": not metrics["phase2"].get("ground_truth_available", True)
            or metrics["phase2"]["precision"] >= BALANCED_THRESHOLDS["constraint_precision"],
            "constraint_recall": not metrics["phase2"].get("ground_truth_available", True)
            or metrics["phase2"]["recall"] >= BALANCED_THRESHOLDS["constraint_recall"],
            "impact_precision": not metrics["phase3"].get("ground_truth_available", True)
            or metrics["phase3"]["precision"] >= BALANCED_THRESHOLDS["impact_precision"],
            "impact_recall": not metrics["phase3"].get("ground_truth_available", True)
            or metrics["phase3"]["recall"] >= BALANCED_THRESHOLDS["impact_recall"],
        }
    )
    if heldout is not None:
        gates.update(_phase1_gates(heldout["phase1"], prefix="heldout_"))
    return gates
