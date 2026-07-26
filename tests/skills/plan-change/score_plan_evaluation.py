"""Behavioral scoring and release gates for plan-change v5 evaluations."""

from __future__ import annotations

from statistics import median
from typing import Any


WEIGHTS = {
    "grounding": 25,
    "propagation": 20,
    "decisions": 20,
    "implementation": 20,
    "verification": 15,
}


def score_expectations(plan: str, expectations: dict[str, list[str]]) -> tuple[float, dict[str, float], list[str]]:
    """Score required semantic claims without treating headings as evidence."""
    missing: list[str] = []
    dimensions: dict[str, float] = {}
    lowered = plan.casefold()
    for dimension, weight in WEIGHTS.items():
        required = expectations.get(dimension, [])
        absent = [value for value in required if value.casefold() not in lowered]
        missing.extend(f"{dimension}:{value}" for value in absent)
        dimensions[dimension] = 100.0 if not required else round(100 * (len(required) - len(absent)) / len(required), 2)
    total = round(sum(WEIGHTS[name] * dimensions[name] / 100 for name in WEIGHTS), 2)
    return total, dimensions, missing


def release_gate(runs: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    if len(runs) < 3:
        return ["evaluation.runs: at least three runs are required"]
    scores = [float(run.get("score", 0)) for run in runs]
    if any(run.get("hard_failures") for run in runs):
        failures.append("evaluation.hard_failures: zero required")
    if median(scores) < 98:
        failures.append("evaluation.median: minimum is 98")
    if min(scores) < 95:
        failures.append("evaluation.minimum: every run minimum is 95")
    for run in runs:
        for name, value in dict(run.get("dimension_scores", {})).items():
            if float(value) < 90:
                failures.append(f"evaluation.dimension: {name} below 90")
    for family in {str(run.get("family", "")) for run in runs} - {""}:
        if sum(run.get("family") == family for run in runs) < 3:
            failures.append(f"evaluation.family_runs: {family} needs at least three runs")
    if any(run.get("downstream_passed") is not True for run in runs):
        failures.append("evaluation.downstream: every configured downstream run must pass")
    return sorted(set(failures))
