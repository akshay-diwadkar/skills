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
    structural_ok: bool
    manifest_validated: tuple[str, ...]


def _refs(value: str) -> set[str]:
    return RUNTIME._refs(value)


def _section_text(plan_text: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in plan_text:
        return ""
    body = plan_text.split(marker, 1)[1]
    if "\n## " in body:
        body = body.split("\n## ", 1)[0]
    return body.strip()


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
    manifest_validated: list[str] = []
    structural_ok = plan is not None and not result.diagnostics
    if not structural_ok or plan is None:
        return ScoreReport(False, dimensions, diagnostics, tuple(missing), False, ())

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
    if dimensions["request_obligations"]:
        manifest_validated.append("request_obligations")

    expected_paths = {
        item["path"]
        for expected in obligation_manifest
        for item in expected.get("planned_paths", [])
    }
    actual_paths = {change.fields.get("path", "") for change in plan.records.get("CH", ())}
    dimensions["planned_paths"] = bool(expected_paths) and expected_paths <= actual_paths
    if dimensions["planned_paths"]:
        manifest_validated.append("planned_paths")

    expected_facts = [
        item
        for expected in obligation_manifest
        for item in expected.get("owner_evidence", [])
    ]
    fact_rows = [
        (record.fields.get("path", ""), record.fields.get("claim", ""))
        for record in plan.records.get("F", ())
    ]
    dimensions["owner_root_cause_evidence"] = bool(expected_facts) and all(
        any(
            item.get("path", "") == path and item.get("claim", "") in claim
            for path, claim in fact_rows
        )
        for item in expected_facts
    )
    if dimensions["owner_root_cause_evidence"]:
        manifest_validated.append("owner_root_cause_evidence")

    expected_deps = {
        tuple(item.get("depends_on", []))
        for expected in obligation_manifest
        for item in expected.get("dependencies", [])
    }
    ordered, dependency_diagnostics = RUNTIME.topological_change_order(plan)
    actual_dep_ok = bool(ordered) and not dependency_diagnostics
    if expected_deps:
        declared = {
            change.id: sorted(_refs(change.fields.get("depends_on", "")))
            for change in plan.records.get("CH", ())
        }
        dimensions["dependency_ordering"] = actual_dep_ok and all(
            list(dep) == declared.get(item.get("ch", ""), [])
            for expected in obligation_manifest
            for item in expected.get("dependencies", [])
            for dep in [item.get("depends_on", [])]
        )
    else:
        dimensions["dependency_ordering"] = actual_dep_ok and all(
            change.fields.get("depends_on") for change in plan.records.get("CH", ())
        )
    if dimensions["dependency_ordering"]:
        manifest_validated.append("dependency_ordering")

    expected_props = [
        item
        for expected in obligation_manifest
        for item in expected.get("propagation", [])
    ]
    prop_rows = [
        (
            record.fields.get("disposition", ""),
            record.fields.get("path", ""),
            record.fields.get("owner", ""),
        )
        for record in plan.records.get("P", ())
    ]
    if expected_props:
        dimensions["propagation_surfaces"] = all(
            any(
                item.get("disposition", "") == disposition
                and item.get("path", "") == path
                and item.get("owner", "") in owner
                for disposition, path, owner in prop_rows
            )
            for item in expected_props
        )
    else:
        dimensions["propagation_surfaces"] = True
    if dimensions["propagation_surfaces"]:
        manifest_validated.append("propagation_surfaces")

    expected_protected = [
        item
        for expected in obligation_manifest
        for item in expected.get("protected_behavior", [])
    ]
    unchanged_blob = "\n".join(record.fields.get("unchanged", "") for record in plan.records.get("SC", ()))
    if expected_protected:
        dimensions["protected_behavior"] = all(
            token in unchanged_blob for item in expected_protected for token in [item.get("text", "")] if token
        )
    else:
        dimensions["protected_behavior"] = True
    if dimensions["protected_behavior"]:
        manifest_validated.append("protected_behavior")

    expected_risk = [
        item
        for expected in obligation_manifest
        for item in expected.get("risk_rollout", [])
    ]
    if expected_risk:
        rollout = _section_text(plan_text, "Rollout and Rollback")
        risk_blob = "\n".join(record.fields.get("risk", "") for record in plan.records.get("R", ()))
        dimensions["risk_and_rollout"] = all(
            (
                (not item.get("risk") or item["risk"] in risk_blob)
                and (not item.get("rollout") or item["rollout"] in rollout)
            )
            for item in expected_risk
        )
    else:
        dimensions["risk_and_rollout"] = True
    if dimensions["risk_and_rollout"]:
        manifest_validated.append("risk_and_rollout")

    expected_verification = [
        item
        for expected in obligation_manifest
        for item in expected.get("verification", [])
    ]
    behavioral_blob = "\n".join(
        " ".join(record.fields.get(field, "") for field in ("covers", "given", "when", "then"))
        for record in plan.records.get("T", ())
    )
    command_blob = "\n".join(record.fields.get("command", "") for record in plan.records.get("T", ()))
    covered = set().union(*(_refs(record.fields.get("covers", "")) for record in plan.records.get("T", ())), set())
    dimensions["verification_coverage"] = not ((plan.ids("SC") | plan.ids("CH")) - covered) and all(
        all(token in behavioral_blob for token in item.get("must_include", []) if token)
        and all(token in command_blob for token in item.get("must_command", []) if token)
        for item in expected_verification
    )
    if dimensions["verification_coverage"]:
        manifest_validated.append("verification_coverage")

    complete = all(dimensions.values()) and not missing
    return ScoreReport(
        complete,
        dimensions,
        diagnostics,
        tuple(missing),
        structural_ok,
        tuple(manifest_validated),
    )
