#!/usr/bin/env python3
"""Check that an implementation bundle preserves and obeys a finalized v5 plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from implementation_contract import Diagnostic, load_contract, parse_plan, validate_v5_repository_binding


def validate_bundle(
    bundle: object, plan_text: str, repo_root: Path, *, require_receipt: bool = False
) -> list[Diagnostic]:
    if not isinstance(bundle, dict):
        return [Diagnostic("bundle.type", "Implementation bundle must be a JSON object.")]
    contract = load_contract()
    for field in contract["required_bundle_fields"]:
        if field not in bundle:
            diagnostics = [Diagnostic("bundle.required", f"Bundle is missing required field `{field}`.")]
            # Continue with plan validation below without indexing untrusted fields.
            break
    else:
        diagnostics = []
    if bundle.get("schema_version") != contract["contract_version"]:
        diagnostics.append(Diagnostic("bundle.schema_version", f"schema_version must be {contract['contract_version']}."))
    if not isinstance(bundle.get("run_id"), str) or not bundle.get("run_id"):
        diagnostics.append(Diagnostic("bundle.run_id", "run_id must be a non-empty string."))
    if bundle.get("status") not in contract["statuses"]:
        diagnostics.append(Diagnostic("bundle.status", f"status must be one of: {', '.join(contract['statuses'])}."))
    for field in ("changes", "verification", "unresolved_changes", "unresolved_tests", "deviations", "residual_risks"):
        if not isinstance(bundle.get(field), list):
            diagnostics.append(Diagnostic("bundle.type", f"{field} must be a list."))
    for field in ("plan", "workspace", "baseline", "final_workspace", "report"):
        if not isinstance(bundle.get(field), dict):
            diagnostics.append(Diagnostic("bundle.type", f"{field} must be an object."))
    plan, plan_diagnostics = parse_plan(plan_text)
    diagnostics.extend(plan_diagnostics)
    diagnostics.extend(validate_v5_repository_binding(plan_text, repo_root))
    if plan is None:
        return diagnostics
    if any(item.code in {"bundle.required", "bundle.type", "bundle.schema_version", "bundle.run_id", "bundle.status"} for item in diagnostics):
        return diagnostics
    normalized = bundle.get("plan", {}).get("normalized") if isinstance(bundle.get("plan"), dict) else None
    if normalized != plan.to_dict():
        diagnostics.append(
            Diagnostic("bundle.plan.preservation", "Bundle must preserve every normalized v5 plan record.")
        )
    changes = {x.id for x in plan.records.get("CH", ())}
    tests = {x.id for x in plan.records.get("T", ())}
    change_ids = [item for row in bundle["changes"] if isinstance(row, dict) for item in row.get("ch_ids", []) if isinstance(item, str)]
    test_ids = [item for row in bundle["verification"] if isinstance(row, dict) for item in row.get("t_ids", []) if isinstance(item, str)]
    listed_changes, listed_tests = set(change_ids), set(test_ids)
    unresolved_changes, unresolved_tests = (
        set(x for x in bundle["unresolved_changes"] if isinstance(x, str)),
        set(x for x in bundle["unresolved_tests"] if isinstance(x, str)),
    )
    if bundle.get("status") == "complete" and (
        changes != listed_changes or tests != listed_tests or len(change_ids) != len(listed_changes) or len(test_ids) != len(listed_tests) or unresolved_changes or unresolved_tests or not bundle["report"].get("summary") or not bundle["final_workspace"]
    ):
        diagnostics.append(
            Diagnostic("bundle.accounting", "Complete run must account for every declared CH and T exactly.")
        )
    receipt = bundle.get("validation_receipt")
    if receipt is not None and bundle.get("status") != "complete":
        diagnostics.append(Diagnostic("bundle.receipt_status", "Only a complete implementation bundle may carry a validation receipt."))
    if require_receipt:
        body = dict(bundle)
        body.pop("validation_receipt", None)
        expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if not isinstance(receipt, dict) or receipt.get("implementation_contract") != 2 or receipt.get("plan_contract") != 5 or receipt.get("sha256") != expected:
            diagnostics.append(Diagnostic("bundle.receipt", "Implementation receipt is missing or does not match the bundle."))
    return diagnostics


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("bundle", type=Path)
    p.add_argument("--format", choices=("text", "json"), default="text")
    a = p.parse_args()
    d = validate_bundle(json.loads(a.bundle.read_text()), a.plan.read_text(), a.repo_root)
    if a.format == "json":
        print(json.dumps({"valid": not d, "diagnostics": [x.to_dict() for x in d]}, indent=2))
    else:
        for x in d:
            print(x)
    return int(bool(d))


if __name__ == "__main__":
    raise SystemExit(main())
