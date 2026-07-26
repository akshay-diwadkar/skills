#!/usr/bin/env python3
"""Check that an implementation bundle preserves and obeys a finalized v5 plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from implementation_contract import Diagnostic, parse_plan, validate_v5_repository_binding


def validate_bundle(
    bundle: object, plan_text: str, repo_root: Path, *, require_receipt: bool = False
) -> list[Diagnostic]:
    if not isinstance(bundle, dict):
        return [Diagnostic("bundle.type", "Implementation bundle must be a JSON object.")]
    plan, diagnostics = parse_plan(plan_text)
    diagnostics.extend(validate_v5_repository_binding(plan_text, repo_root))
    if plan is None:
        return diagnostics
    normalized = bundle.get("plan", {}).get("normalized") if isinstance(bundle.get("plan"), dict) else None
    if normalized != plan.to_dict():
        diagnostics.append(
            Diagnostic("bundle.plan.preservation", "Bundle must preserve every normalized v5 plan record.")
        )
    changes = {x.id for x in plan.records.get("CH", ())}
    tests = {x.id for x in plan.records.get("T", ())}
    listed_changes = {
        item for row in bundle.get("changes", []) if isinstance(row, dict) for item in row.get("ch_ids", [])
    }
    listed_tests = {
        item for row in bundle.get("verification", []) if isinstance(row, dict) for item in row.get("t_ids", [])
    }
    unresolved_changes, unresolved_tests = (
        set(bundle.get("unresolved_changes", [])),
        set(bundle.get("unresolved_tests", [])),
    )
    if bundle.get("status") == "complete" and (
        changes != listed_changes or tests != listed_tests or unresolved_changes or unresolved_tests
    ):
        diagnostics.append(
            Diagnostic("bundle.accounting", "Complete run must account for every declared CH and T exactly.")
        )
    receipt = bundle.get("validation_receipt")
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
