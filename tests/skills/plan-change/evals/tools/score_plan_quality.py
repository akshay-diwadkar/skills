"""Deterministic plan-quality scorer for the offline v7-quality fixture suite.

Reports coverage of request obligations, owner and root-cause evidence, planned
paths, dependency ordering, propagation surfaces, protected behavior, risk and
rollout requirements, and verification coverage. Runs entirely on the parsed
plan and a fixture-owned manifest: no provider, model, agent harness, or
network access.
"""

from __future__ import annotations

import re
from typing import Any

ID_RE = re.compile(r"[A-Z]{1,3}-\d+")
DIMENSIONS = ("obligations", "owners", "paths", "ordering", "propagation", "protected", "risk", "verification")


def _refs(value: str | None) -> set[str]:
    return set(ID_RE.findall(value or ""))


def _records(plan: Any, kind: str) -> tuple:
    return plan.records.get(kind, ())


def _check_obligations(plan: Any, manifest: dict[str, Any]) -> bool:
    pairs = {(record.fields.get("anchor", ""), record.fields.get("obligation", "")) for record in _records(plan, "RQ")}
    return all((item["anchor"], item["obligation"]) in pairs for item in manifest.get("obligations", []))


def _check_owners(plan: Any, manifest: dict[str, Any]) -> bool:
    referenced: set[str] = set()
    for change in _records(plan, "CH"):
        referenced |= _refs(change.fields.get("evidence", "")) | _refs(change.fields.get("owner", ""))
    facts = {record.id: record for record in _records(plan, "F")}
    for owner in manifest.get("owners", []):
        if not any(
            fact.id in referenced
            and fact.fields.get("path", "").replace("\\", "/") == owner["path"]
            and fact.fields.get("anchor", "") == owner["anchor"]
            for fact in facts.values()
        ):
            return False
    return True


def _check_paths(plan: Any, manifest: dict[str, Any]) -> bool:
    planned = {change.fields.get("path", "") for change in _records(plan, "CH")}
    return planned == set(manifest.get("paths", []))


def _execution_order(plan: Any) -> list[str] | None:
    changes = {record.id: record for record in _records(plan, "CH")}
    edges = {
        identifier: _refs(record.fields.get("depends_on", "")) & set(changes)
        for identifier, record in changes.items()
    }
    remaining = set(changes)
    ordered: list[str] = []
    while remaining:
        ready = sorted(identifier for identifier in remaining if not edges[identifier] & remaining)
        if not ready:
            return None
        identifier = ready[0]
        ordered.append(identifier)
        remaining.discard(identifier)
    return ordered


def _check_ordering(plan: Any, manifest: dict[str, Any]) -> bool:
    changes = {record.id: record for record in _records(plan, "CH")}
    order = _execution_order(plan)
    if order is None:
        return False
    for before, after in manifest.get("order", []):
        after_change = changes.get(after)
        if after_change is None or before not in _refs(after_change.fields.get("depends_on", "")):
            return False
        if order.index(before) > order.index(after):
            return False
    return True


def _check_propagation(plan: Any, manifest: dict[str, Any]) -> bool:
    p_paths = {record.fields.get("path", "") for record in _records(plan, "P")}
    declared = {
        change.fields.get("path", "")
        for change in _records(plan, "CH")
        if change.fields.get("propagation", "") in {"local", "none"}
    }
    accounted = p_paths | declared
    return set(manifest.get("propagation_surfaces", [])) <= accounted


def _check_protected(plan: Any, manifest: dict[str, Any]) -> bool:
    unchanged = {record.fields.get("unchanged", "") for record in _records(plan, "SC")}
    return all(any(item in text for text in unchanged) for item in manifest.get("protected", []))


def _check_risk(plan: Any, manifest: dict[str, Any]) -> bool:
    declared = set(manifest.get("risk_domains", []))
    if not declared <= plan.risk_domains:
        return False
    if declared and "Rollout and Rollback" not in plan.sections:
        return False
    if plan.tier == "high-risk" and not (plan.records.get("B") and plan.records.get("R")):
        return False
    for risk in manifest.get("risks", []):
        if not any(
            record.fields.get("owner", "") == risk["owner"] and record.fields.get("tests", "") == risk["tests"]
            for record in _records(plan, "R")
        ):
            return False
    return True


def _check_verification(plan: Any, manifest: dict[str, Any]) -> bool:
    verification = [record.fields for record in _records(plan, "T")]
    for entry in manifest.get("verification", []):
        identifiers = set(entry["covers"])
        behavior = entry.get("then", "")
        if not any(
            identifiers <= _refs(item.get("covers", "")) and behavior in item.get("then", "")
            for item in verification
        ):
            return False
    return True


def score_plan(plan: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    """Score one parsed plan against its scenario manifest."""
    dimensions = {
        "obligations": _check_obligations(plan, manifest),
        "owners": _check_owners(plan, manifest),
        "paths": _check_paths(plan, manifest),
        "ordering": _check_ordering(plan, manifest),
        "propagation": _check_propagation(plan, manifest),
        "protected": _check_protected(plan, manifest),
        "risk": _check_risk(plan, manifest),
        "verification": _check_verification(plan, manifest),
    }
    counts = {kind: len(_records(plan, kind)) for kind in ("SC", "RQ", "F", "D", "CH", "P", "B", "R", "T")}
    missing = sorted(name for name in DIMENSIONS if not dimensions[name])
    return {
        "plan_title": plan.title,
        "dimensions": dimensions,
        "missing": missing,
        "counts": counts,
        "complete": not missing,
    }
