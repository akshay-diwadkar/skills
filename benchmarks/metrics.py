from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .phase1_metrics import aggregate_phase1_metrics


def _path(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return str(value.get("path", ""))
    return ""


def _set(values: Iterable[object]) -> set[str]:
    return {path for value in values if (path := _path(value))}


def _phase_metrics(
    outcomes: Sequence[Mapping[str, Any]], predicted_field: str, expected_field: str
) -> dict[str, float | int | bool]:
    true_positive = predicted = expected = 0
    for outcome in outcomes:
        predicted_set = _set(outcome.get(predicted_field, []))
        expected_set = _set(outcome.get(expected_field, []))
        true_positive += len(predicted_set & expected_set)
        predicted += len(predicted_set)
        expected += len(expected_set)
    return {
        "ground_truth_available": expected > 0,
        "true_positive": true_positive,
        "predicted": predicted,
        "expected": expected,
        "precision": true_positive / predicted if predicted else (1.0 if not expected else 0.0),
        "recall": true_positive / expected if expected else 1.0,
    }


def aggregate_benchmark_metrics(outcomes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Score phases independently; no Phase 2/3 path can affect owner precision."""
    return {
        "phase1": aggregate_phase1_metrics(outcomes),
        "phase2": _phase_metrics(outcomes, "constraints", "expected_constraints"),
        "phase3": _phase_metrics(outcomes, "impacts", "expected_impacts"),
    }
