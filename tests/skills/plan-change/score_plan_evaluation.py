"""Parsed-record scoring and model/scenario release gates for plan-change v5."""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import Plan, parse_plan  # noqa: E402

WEIGHTS = {
    "grounding": 20,
    "propagation": 20,
    "decisions": 15,
    "implementation": 15,
    "blueprints": 15,
    "verification": 15,
}


def _record_text(plan: Plan, kind: str, fields: tuple[str, ...]) -> str:
    return " ".join(record.fields.get(field, "") for record in plan.records.get(kind, ()) for field in fields).casefold()


def _dimension_checks(plan: Plan, dimension: str, expected: dict[str, Any]) -> list[tuple[str, bool]]:
    checks: list[tuple[str, bool]] = []
    if dimension == "grounding":
        paths = {record.fields.get("path", "") for record in plan.records.get("F", ())}
        anchors = {record.fields.get("anchor", "") for record in plan.records.get("F", ())}
        checks.extend((f"path={value}", value in paths) for value in expected.get("paths", []))
        checks.extend((f"anchor={value}", value in anchors) for value in expected.get("anchors", []))
    elif dimension == "propagation":
        surfaces = {record.fields.get("surface", "") for record in plan.records.get("P", ())}
        checks.extend((f"surface={value}", value in surfaces) for value in expected.get("surfaces", []))
        checks.append(("typed-ownership", all(record.fields.get("owner", "").startswith("CH-") for record in plan.records.get("P", ()))))
    elif dimension == "decisions":
        text = _record_text(plan, "D", ("selected", "rejected", "drawback"))
        checks.extend((f"term={value}", value.casefold() in text) for value in expected.get("terms", []))
        checks.append(("evidence-links", all(record.fields.get("evidence") for record in plan.records.get("D", ()))))
    elif dimension == "implementation":
        paths = {record.fields.get("path", "") for record in plan.records.get("CH", ())}
        text = _record_text(plan, "CH", ("change", "anchor"))
        checks.extend((f"path={value}", value in paths) for value in expected.get("paths", []))
        checks.extend((f"term={value}", value.casefold() in text) for value in expected.get("terms", []))
        traced = {change for row in plan.traceability for change in row.changes}
        checks.append(("trace-ownership", plan.ids("CH") <= traced))
    elif dimension == "blueprints":
        domains = {domain for blueprint in plan.blueprints for domain in blueprint.domains}
        checks.extend((f"domain={value}", value in domains) for value in expected.get("domains", []))
        minimum = int(expected.get("minimum", 0))
        checks.append((f"minimum={minimum}", len(plan.blueprints) >= minimum))
    elif dimension == "verification":
        text = _record_text(plan, "T", ("given", "when", "then", "command"))
        checks.extend((f"term={value}", value.casefold() in text) for value in expected.get("terms", []))
        minimum = int(expected.get("minimum", 1))
        checks.append((f"minimum={minimum}", len(plan.records.get("T", ())) >= minimum))
        traced = {test for row in plan.traceability for test in row.tests}
        checks.append(("trace-ownership", plan.ids("T") <= traced))
    return checks or [("no-expectations", True)]


def score_expectations(plan_text: str, expectations: dict[str, Any]) -> tuple[float, dict[str, float], list[str]]:
    plan, diagnostics = parse_plan(plan_text)
    if plan is None or diagnostics:
        return 0.0, {name: 0.0 for name in WEIGHTS}, ["parsed:valid-plan"]
    missing: list[str] = []
    dimensions: dict[str, float] = {}
    for dimension in WEIGHTS:
        checks = _dimension_checks(plan, dimension, dict(expectations.get(dimension, {})))
        passed = sum(ok for _, ok in checks)
        dimensions[dimension] = round(100 * passed / len(checks), 2)
        missing.extend(f"{dimension}:{label}" for label, ok in checks if not ok)
    total = round(sum(WEIGHTS[name] * dimensions[name] / 100 for name in WEIGHTS), 2)
    return total, dimensions, missing


def release_gate(runs: list[dict[str, Any]]) -> list[str]:
    if not runs:
        return ["evaluation.runs: evaluation report is empty"]
    failures: list[str] = []
    pairs = {(str(run.get("model_label", "")), str(run.get("scenario", ""))) for run in runs}
    for model_label, scenario in sorted(pairs):
        label = f"{model_label}/{scenario}"
        pair_runs = [
            run for run in runs
            if run.get("model_label") == model_label and run.get("scenario") == scenario
        ]
        scores = [float(run.get("score", 0)) for run in pair_runs]
        if any(run.get("hard_failures") for run in pair_runs):
            failures.append(f"evaluation.hard_failures: {label} requires zero")
        if any(bool(run.get("repository_mutation")) for run in pair_runs):
            failures.append(f"evaluation.repository_mutation: {label} requires zero")
        if median(scores) < 98:
            failures.append(f"evaluation.median: {label} minimum is 98")
        if min(scores) < 95:
            failures.append(f"evaluation.minimum: {label} every run minimum is 95")
        for run in pair_runs:
            for name, value in dict(run.get("dimension_scores", {})).items():
                if float(value) < 90:
                    failures.append(f"evaluation.dimension: {label} {name} below 90")
        if any(run.get("downstream_status") == "failed" for run in pair_runs):
            failures.append(f"evaluation.downstream: {label} every configured downstream run must pass")
        successful = [
            run for run in pair_runs
            if not run.get("hard_failures")
            and float(run.get("score", 0)) >= 95
            and not run.get("repository_mutation")
            and run.get("downstream_status") != "failed"
        ]
        if len(successful) < 3:
            failures.append(f"evaluation.pair_runs: {label} needs at least three successful runs")
    return sorted(set(failures))
