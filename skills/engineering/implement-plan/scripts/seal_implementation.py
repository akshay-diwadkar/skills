#!/usr/bin/env python3
"""Seal one implementation report without inspecting unrelated worktree paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from implementation_contract import plan_contract_version, sha256_file, validate_plan_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    plan_text = args.plan.read_text(encoding="utf-8")
    plan, diagnostics = validate_plan_text(plan_text, root)
    if diagnostics or plan is None or plan_contract_version(plan_text) != 6:
        for diagnostic in diagnostics:
            print(diagnostic)
        return 1
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        print("bundle must be an object")
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
        "implementation_contract": 4,
        "plan_contract": 6,
        "scope": "planned-and-agent-reported-paths-only",
        "sha256": hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "touched_paths": sorted(touched)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
