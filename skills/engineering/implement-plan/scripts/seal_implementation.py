#!/usr/bin/env python3
"""Seal one implementation report without inspecting unrelated worktree paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from implementation_contract import plan_contract_version, sha256_file, validate_plan_text


def _snapshot_path(output_path: Path, repo_path: str) -> Path:
    name = hashlib.sha256(repo_path.encode("utf-8")).hexdigest() + ".before"
    return output_path.parent / "snapshots" / name


def _verify_plan_with_recorded_state(
    plan: object, output_path: Path, diagnostics: list
) -> str | None:
    """Verify the sealed plan against the bundle's recorded pre-state snapshots.

    The plan's evidence describes the state before implementation, so targets
    that the plan changed are expected to fail anchor verification against the
    current worktree. When every failure is a fact.anchor on a path that has a
    matching before-snapshot and the anchor is present in the cited snapshot
    range, the plan is verified against the recorded pre-state. Any other
    diagnostic kind or a missing snapshot fails closed.
    """
    stale = [item for item in diagnostics if item.code == "fact.anchor"]
    if plan is None or len(stale) != len(diagnostics):
        return None
    records = {record.id: record for record in plan.records.get("F", ())}
    failures: list[str] = []
    for item in stale:
        record = records.get(item.record)
        snapshot = _snapshot_path(output_path, item.path)
        if record is None or not snapshot.is_file():
            failures.append(item.record)
            continue
        excerpt = snapshot.read_text(encoding="utf-8").splitlines()
        try:
            start, end = (int(part) for part in record.fields["lines"].split("-"))
        except (ValueError, KeyError):
            failures.append(item.record)
            continue
        cited = "\n".join(excerpt[max(start - 1, 0) : end])
        if record.fields["anchor"] not in cited:
            failures.append(item.record)
    if failures:
        return None
    return "recorded-pre-state-snapshots"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    plan_text = args.plan.read_text(encoding="utf-8")
    plan, diagnostics = validate_plan_text(plan_text, root)
    verification_mode = None
    if diagnostics and plan is not None:
        verification_mode = _verify_plan_with_recorded_state(plan, args.bundle, diagnostics)
        if verification_mode is not None:
            diagnostics = []
    contract_version = plan_contract_version(plan_text)
    if diagnostics or plan is None or contract_version not in {6, 7}:
        for diagnostic in diagnostics:
            print(diagnostic)
        return 1
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        print("bundle must be an object")
        return 1
    if verification_mode is not None:
        bundle["plan_verification"] = verification_mode
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
        "plan_contract": contract_version,
        "scope": "planned-and-agent-reported-paths-only",
        "sha256": hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "touched_paths": sorted(touched)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
