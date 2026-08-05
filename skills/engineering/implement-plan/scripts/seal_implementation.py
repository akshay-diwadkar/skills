#!/usr/bin/env python3
"""Seal one implementation report without inspecting unrelated worktree paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from implementation_contract import (
    load_contract,
    plan_contract_version,
    sha256_file,
    validate_bundle_against_plan,
    validate_plan_for_completion,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    plan_text = args.plan.read_text(encoding="utf-8")
    contract = load_contract()
    version = plan_contract_version(plan_text)
    supported = set(contract["supported_plan_contract_versions"])
    if version not in supported:
        print(f"contract.unsupported: plan-contract version {version!r} is not supported")
        return 1
    plan, diagnostics = validate_plan_for_completion(plan_text)
    if diagnostics or plan is None:
        for diagnostic in diagnostics:
            print(diagnostic)
        return 1
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        print("bundle must be an object")
        return 1
    order_errors = validate_bundle_against_plan(
        bundle, plan, plan_text, version, require_completion=True, repo_root=root
    )
    if order_errors:
        for error in order_errors:
            print(error)
        return 1
    planned = {record.fields.get("path") for record in plan.records.get("CH", ())}
    touched = {
        path
        for change in bundle.get("changes", [])
        if isinstance(change, dict)
        for path in change.get("paths", [])
        if isinstance(path, str)
    }
    unauthorized = sorted(path for path in touched if path not in planned)
    if unauthorized:
        print("agent-reported touched paths are not planned: " + ", ".join(unauthorized))
        return 1
    bundle["targeted_after_sha256"] = {path: sha256_file(root / path) for path in sorted(touched)}
    bundle["status"] = "complete"
    canonical = dict(bundle)
    canonical.pop("validation_receipt", None)
    bundle["validation_receipt"] = {
        "implementation_contract": int(contract["contract_version"]),
        "plan_contract": version,
        "scope": "planned-and-agent-reported-paths-only",
        "sha256": hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "touched_paths": sorted(touched)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
