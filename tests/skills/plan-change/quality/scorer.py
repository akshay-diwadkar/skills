"""Deterministic plan-quality scoring for plan-contract v7 fixtures."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[4] / "skills" / "engineering" / "plan-change" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("plan_quality_runtime", SCRIPTS / "plan_runtime.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load plan runtime")
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)


@dataclass(frozen=True)
class ScoreReport:
    complete: bool
    dimensions: dict[str, bool]
    diagnostics: tuple[str, ...]
    missing_obligations: tuple[str, ...]


def _refs(value: str) -> set[str]:
    return RUNTIME._refs(value)


def score_plan(
    plan_text: str,
    repo_root: Path,
    *,
    request_bytes: bytes,
    obligation_manifest: list[dict[str, Any]],
    handoff_item: str | None = None,
) -> ScoreReport:
    result = RUNTIME.validate_draft(
        plan_text,
        repo_root,
        request_bytes=request_bytes,
        handoff_item=handoff_item,
    )
    diagnostics = tuple(f"{item.code}:{item.record or '-'}:{item.message}" for item in result.diagnostics)
    plan = result.plan
    dimensions = {
        "request_obligations": False,
        "owner_root_cause_evidence": False,
        "planned_paths": False,
        "dependency_ordering": False,
        "propagation_surfaces": False,
        "protected_behavior": False,
        "risk_and_rollout": False,
        "verification_coverage": False,
    }
    missing: list[str] = []
    if plan is None or result.diagnostics:
        return ScoreReport(False, dimensions, diagnostics, tuple(missing))

    rq_texts = {
        (record.fields.get("obligation", ""), record.fields.get("anchor", ""))
        for record in plan.records.get("RQ", ())
    }
    for expected in obligation_manifest:
        needle = expected["obligation"]
        anchor = expected.get("anchor", "")
        if not any(needle in obligation and (not anchor or anchor in listed_anchor) for obligation, listed_anchor in rq_texts):
            missing.append(expected["id"])
    dimensions["request_obligations"] = not missing and bool(plan.records.get("RQ"))

    facts = plan.records.get("F", ())
    changes = plan.records.get("CH", ())
    dimensions["owner_root_cause_evidence"] = bool(facts) and all(
        change.fields.get("status") != "existing" or _refs(change.fields.get("evidence", "")) for change in changes
    )
    dimensions["planned_paths"] = all(bool(change.fields.get("path")) for change in changes) and bool(changes)
    ordered, dependency_diagnostics = RUNTIME.topological_change_order(plan)
    dimensions["dependency_ordering"] = bool(ordered) and not dependency_diagnostics and all(
        change.fields.get("depends_on") for change in changes
    )
    shared = [change for change in changes if change.fields.get("locality") == "shared"]
    owned = {
        owner
        for record in plan.records.get("P", ())
        for owner in _refs(record.fields.get("owner", ""))
    }
    dimensions["propagation_surfaces"] = all(change.id in owned for change in shared)
    dimensions["protected_behavior"] = all(
        RUNTIME._substantive(record.fields.get("unchanged", "")) for record in plan.records.get("SC", ())
    )
    if plan.tier == "high-risk" or any(change.fields.get("reversibility") == "irreversible" for change in changes):
        dimensions["risk_and_rollout"] = bool(plan.records.get("B")) and bool(plan.records.get("R")) and (
            "Rollout and Rollback" in plan.sections or not (plan.risk_domains & RUNTIME.ROLLOUT_DOMAINS)
            and not any(change.fields.get("reversibility") == "irreversible" for change in changes)
        )
        if plan.risk_domains & RUNTIME.ROLLOUT_DOMAINS or any(
            change.fields.get("reversibility") == "irreversible" for change in changes
        ):
            dimensions["risk_and_rollout"] = (
                bool(plan.records.get("B"))
                and bool(plan.records.get("R"))
                and "Rollout and Rollback" in plan.sections
            )
    else:
        dimensions["risk_and_rollout"] = True
    covered = set().union(*(_refs(record.fields.get("covers", "")) for record in plan.records.get("T", ())), set())
    dimensions["verification_coverage"] = not ((plan.ids("SC") | plan.ids("CH")) - covered)

    complete = all(dimensions.values()) and not missing
    return ScoreReport(complete, dimensions, diagnostics, tuple(missing))
