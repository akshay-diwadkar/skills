#!/usr/bin/env python3
"""Validate an implementation-run bundle against its plan and current workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from implementation_contract import Diagnostic, git_status, load_contract, parse_plan, sha256_bytes, sha256_file


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str) and item] if isinstance(value, list) else []


def _placeholder(value: Any, path: str = "bundle") -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if isinstance(value, dict):
        for key, item in value.items():
            diagnostics.extend(_placeholder(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            diagnostics.extend(_placeholder(item, f"{path}[{index}]"))
    elif isinstance(value, str) and value.strip().casefold() in {"replace", "tbd", "todo", "unknown"}:
        diagnostics.append(Diagnostic("bundle.placeholder", f"Unresolved placeholder at {path}."))
    return diagnostics


def _actual_run_paths(bundle: dict[str, Any], repo_root: Path) -> tuple[set[str], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    workspace = bundle.get("workspace", {})
    initial = {item.get("path", ""): item for item in workspace.get("initial_dirty", []) if isinstance(item, dict)}
    current = git_status(repo_root)
    target_records = {
        record.get("path", ""): record
        for record in workspace.get("targets", [])
        if isinstance(record, dict) and record.get("path")
    }
    changed_initial_targets: set[str] = set()
    for path, item in initial.items():
        if not path:
            continue
        target = repo_root / path
        changed = sha256_file(target) != item.get("sha256", "")
        if path not in target_records:
            if changed:
                diagnostics.append(Diagnostic("workspace.dirty.modified", f"Initial user-owned path changed during the run: {path}."))
        elif changed:
            if target_records[path].get("authorization") == "user-authorized":
                changed_initial_targets.add(path)
            else:
                diagnostics.append(Diagnostic("workspace.target.concurrent", f"Dirty target changed without recorded authorization: {path}."))
    return (set(current) - set(initial)) | changed_initial_targets, diagnostics


def validate_bundle(bundle: Any, plan_text: str, repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not isinstance(bundle, dict):
        return [Diagnostic("bundle.type", "Implementation bundle must be a JSON object.")]
    contract = load_contract()
    for field in contract["required_bundle_fields"]:
        if field not in bundle:
            diagnostics.append(Diagnostic("bundle.field.missing", f"Missing required field {field}."))
    if bundle.get("schema_version") != contract["contract_version"]:
        diagnostics.append(Diagnostic("bundle.version", "Unsupported implementation bundle schema version."))
    if bundle.get("status") not in contract["statuses"]:
        diagnostics.append(Diagnostic("bundle.status", "Invalid implementation status."))
    diagnostics.extend(_placeholder(bundle))

    plan, plan_diagnostics = parse_plan(plan_text)
    diagnostics.extend(plan_diagnostics)
    recorded_plan = bundle.get("plan", {})
    if isinstance(recorded_plan, dict):
        if recorded_plan.get("sha256") != sha256_bytes(plan_text.encode("utf-8")):
            diagnostics.append(Diagnostic("bundle.plan.hash", "Plan snapshot hash does not match the supplied plan."))
        for field in ("contract_version", "tier", "task_type"):
            if recorded_plan.get(field) != plan.to_dict().get(field):
                diagnostics.append(Diagnostic("bundle.plan.metadata", f"Recorded plan {field} does not match parsed plan."))

    workspace = bundle.get("workspace", {})
    targets = workspace.get("targets", []) if isinstance(workspace, dict) else []
    recorded_change_paths = {
        path
        for change in bundle.get("changes", [])
        if isinstance(change, dict)
        for path in _strings(change.get("paths"))
    }
    for target in targets:
        if (
            isinstance(target, dict)
            and target.get("initial_status")
            and target.get("authorization") != "user-authorized"
            and (bundle.get("status") != "blocked" or target.get("path") in recorded_change_paths)
        ):
            diagnostics.append(Diagnostic("workspace.target.dirty", f"Target path was dirty without authorization: {target.get('path')}."))

    for index, baseline in enumerate(bundle.get("baseline", [])):
        if not isinstance(baseline, dict):
            diagnostics.append(Diagnostic("baseline.type", f"baseline[{index}] must be an object."))
            continue
        command = baseline.get("command", "")
        if not isinstance(command, str) or not command.strip():
            diagnostics.append(Diagnostic("baseline.command", "Baseline command is required."))
        elif any(forbidden in command.casefold() for forbidden in contract["forbidden_automatic_commands"]):
            diagnostics.append(Diagnostic("baseline.command.unsafe", f"Forbidden automatic command recorded: {command}."))
        if baseline.get("status") not in {"passed", "failed", "skipped"}:
            diagnostics.append(Diagnostic("baseline.status", "Baseline status must be passed, failed, or skipped."))
        if not isinstance(baseline.get("exit_code"), int):
            diagnostics.append(Diagnostic("baseline.exit_code", "Baseline exit_code must be an integer."))
        evidence = baseline.get("evidence", "")
        if not isinstance(evidence, str) or not evidence:
            diagnostics.append(Diagnostic("baseline.evidence", "Baseline evidence path is required."))
        elif not Path(evidence).is_file():
            diagnostics.append(Diagnostic("baseline.evidence.missing", f"Baseline evidence file does not exist: {evidence}."))

    plan_change_ids = {item["id"] for item in plan.changes}
    plan_test_ids = {item["id"] for item in plan.tests}
    plan_paths = {item.get("path", "") for item in plan.changes}
    accounted_changes: set[str] = set()
    declared_paths: set[str] = set()
    for index, change in enumerate(bundle.get("changes", [])):
        if not isinstance(change, dict):
            diagnostics.append(Diagnostic("change.type", f"changes[{index}] must be an object."))
            continue
        kind = change.get("kind")
        if kind not in contract["change_kinds"]:
            diagnostics.append(Diagnostic("change.kind", f"changes[{index}] has invalid kind."))
        ch_ids = set(_strings(change.get("ch_ids")))
        paths = set(_strings(change.get("paths")))
        accounted_changes.update(ch_ids)
        declared_paths.update(paths)
        for identifier in ch_ids - plan_change_ids:
            diagnostics.append(Diagnostic("change.plan.unknown", f"Change record references unknown {identifier}."))
        if kind == "planned" and any(path not in plan_paths for path in paths):
            diagnostics.append(Diagnostic("change.path.unplanned", f"Planned record contains path outside its CH records: {sorted(paths - plan_paths)}."))
        if not isinstance(change.get("before_sha256"), str) or not change.get("before_sha256"):
            diagnostics.append(Diagnostic("change.hash.before", "Change record requires before_sha256."))
        if not isinstance(change.get("after_sha256"), str) or not change.get("after_sha256"):
            diagnostics.append(Diagnostic("change.hash.after", "Change record requires after_sha256."))
        if kind == "mechanical-propagation":
            policy = change.get("policy", {})
            for flag in contract["mechanical_propagation"]["required_flags"]:
                if not isinstance(policy, dict) or policy.get(flag) is not True:
                    diagnostics.append(Diagnostic("change.mechanical.policy", f"Mechanical change must set {flag}=true."))
            if not isinstance(policy, dict) or policy.get("necessary_for") not in contract["mechanical_propagation"]["allowed_reasons"]:
                diagnostics.append(Diagnostic("change.mechanical.reason", "Mechanical change has an invalid necessity reason."))
            if not _strings(change.get("evidence")) or not _strings(change.get("verification")):
                diagnostics.append(Diagnostic("change.mechanical.proof", "Mechanical change requires evidence and verification."))

    unresolved_changes = set(_strings(bundle.get("unresolved_changes")))
    unresolved_tests = set(_strings(bundle.get("unresolved_tests")))
    for identifier in unresolved_changes - plan_change_ids:
        diagnostics.append(Diagnostic("unresolved.change.unknown", f"Unknown unresolved change {identifier}."))
    for identifier in unresolved_tests - plan_test_ids:
        diagnostics.append(Diagnostic("unresolved.test.unknown", f"Unknown unresolved test {identifier}."))
    if accounted_changes | unresolved_changes != plan_change_ids:
        diagnostics.append(Diagnostic("change.accounting", "Every plan CH-n must be implemented or unresolved exactly."))

    accounted_tests: set[str] = set()
    plan_test_commands = {item["id"]: item.get("command", "") for item in plan.tests}
    for index, verification in enumerate(bundle.get("verification", [])):
        if not isinstance(verification, dict):
            diagnostics.append(Diagnostic("verification.type", f"verification[{index}] must be an object."))
            continue
        test_ids = set(_strings(verification.get("t_ids")))
        accounted_tests.update(test_ids)
        for identifier in test_ids - plan_test_ids:
            diagnostics.append(Diagnostic("verification.test.unknown", f"Verification references unknown {identifier}."))
        command = verification.get("command", "")
        if not isinstance(command, str) or not command.strip():
            diagnostics.append(Diagnostic("verification.command", "Verification command is required."))
        elif any(forbidden in command.casefold() for forbidden in contract["forbidden_automatic_commands"]):
            diagnostics.append(Diagnostic("verification.command.unsafe", f"Forbidden automatic command recorded: {command}."))
        for identifier in test_ids & plan_test_ids:
            if command != plan_test_commands[identifier]:
                diagnostics.append(Diagnostic("verification.command.mismatch", f"Command for {identifier} does not match the approved plan."))
        if verification.get("status") not in contract["verification_statuses"]:
            diagnostics.append(Diagnostic("verification.status", "Invalid verification status."))
        if not isinstance(verification.get("exit_code"), int):
            diagnostics.append(Diagnostic("verification.exit_code", "Verification exit_code must be an integer."))
        if not isinstance(verification.get("evidence"), str) or not verification.get("evidence"):
            diagnostics.append(Diagnostic("verification.evidence", "Verification evidence path is required."))
        elif not Path(verification["evidence"]).is_file():
            diagnostics.append(Diagnostic("verification.evidence.missing", f"Verification evidence file does not exist: {verification['evidence']}."))
    if accounted_tests | unresolved_tests != plan_test_ids:
        diagnostics.append(Diagnostic("verification.accounting", "Every plan T-n must be verified or unresolved exactly."))

    actual_paths, workspace_diagnostics = _actual_run_paths(bundle, repo_root)
    diagnostics.extend(workspace_diagnostics)
    final_workspace = bundle.get("final_workspace", {})
    recorded_paths = set(_strings(final_workspace.get("changed_paths"))) if isinstance(final_workspace, dict) else set()
    if recorded_paths != actual_paths:
        diagnostics.append(Diagnostic("workspace.delta", f"Recorded changed paths {sorted(recorded_paths)} do not match workspace {sorted(actual_paths)}."))
    for path in actual_paths - declared_paths:
        diagnostics.append(Diagnostic("workspace.path.undeclared", f"Changed path has no change record: {path}."))
    if bundle.get("status") == "complete":
        for path in declared_paths - actual_paths:
            diagnostics.append(Diagnostic("workspace.path.no_diff", f"Complete run declares a path with no resulting delta: {path}."))

    if bundle.get("status") in {"complete", "partial", "blocked"}:
        initial_paths = {
            item.get("path", "")
            for item in workspace.get("initial_dirty", [])
            if isinstance(item, dict) and item.get("path")
        }
        expected_preserved = initial_paths - actual_paths
        recorded_preserved = set(_strings(final_workspace.get("preserved_initial_dirty_paths"))) if isinstance(final_workspace, dict) else set()
        if recorded_preserved != expected_preserved:
            diagnostics.append(Diagnostic("workspace.dirty.accounting", f"Preserved dirty paths must be exactly {sorted(expected_preserved)}."))

    if bundle.get("status") == "complete":
        if unresolved_changes or unresolved_tests:
            diagnostics.append(Diagnostic("complete.unresolved", "Complete run cannot contain unresolved CH/T records."))
        if any(item.get("status") != "passed" for item in bundle.get("verification", []) if isinstance(item, dict)):
            diagnostics.append(Diagnostic("complete.verification", "Complete run requires every verification record to pass."))
    elif bundle.get("status") in {"partial", "blocked"} and not (unresolved_changes or unresolved_tests):
        diagnostics.append(Diagnostic("incomplete.unresolved", "Partial or blocked run must identify unresolved CH/T records."))
    if bundle.get("status") in {"complete", "partial", "blocked"} and not bundle.get("report", {}).get("summary"):
        diagnostics.append(Diagnostic("final.report", "Final run status requires a non-empty report summary."))
    return diagnostics


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        plan_text = args.plan.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    diagnostics = validate_bundle(bundle, plan_text, args.repo_root.resolve())
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": [item.to_dict() for item in diagnostics]}, indent=2))
    elif diagnostics:
        print("Implementation check findings:")
        for item in diagnostics:
            print(f"- {item}")
    else:
        print("Implementation check passed.")
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
