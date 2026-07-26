"""Provider-neutral strict release gate for v5 plan evaluations."""

from __future__ import annotations

from statistics import median
from typing import Any


def release_gate(runs: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    if len(runs) < 3:
        failures.append("evaluation.runs: at least three runs are required")
        return failures
    scores = [float(run.get("score", 0)) for run in runs]
    blueprints = [float(run.get("blueprint_score", 0)) for run in runs]
    if any(run.get("hard_failures", 0) for run in runs):
        failures.append("evaluation.hard_failures: zero required")
    if median(scores) < 95:
        failures.append("evaluation.median: minimum is 95")
    if min(scores) < 90:
        failures.append("evaluation.minimum: every run minimum is 90")
    if min(blueprints) < 90:
        failures.append("evaluation.blueprint: every standard/high-risk blueprint minimum is 90")
    return failures
