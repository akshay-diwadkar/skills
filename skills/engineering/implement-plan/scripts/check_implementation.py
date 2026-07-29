#!/usr/bin/env python3
"""Validate implementation-contract v3 bundles and reconcile the real workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from implementation_contract import (
    Diagnostic,
    git_status,
    load_contract,
    parse_plan,
    plan_contract_version,
    repository_state,
    sha256_file,
)
from plan_runtime import BINDING_CATEGORIES, binding_digest, plan_digest


def _matches_type(value: object, expected: str) -> bool:
    return {
        "string": isinstance(value, str),
        "string-or-null": value is None or isinstance(value, str),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string-array": isinstance(value, list) and all(isinstance(item, str) for item in value),
        "integer": isinstance(value, int) and not isinstance(value, bool),
    }.get(expected, False)


def _row_diagnostics(value: object, schema_name: str, label: str, contract: dict[str, Any]) -> list[Diagnostic]:
    if not isinstance(value, dict):
        return [Diagnostic("bundle.row_type", f"{label} must be an object.")]
    diagnostics: list[Diagnostic] = []
    required = contract["schemas"][schema_name]["required"]
    optional = contract["schemas"][schema_name].get("optional", {})
    for field, expected in required.items():
        if field not in value:
            diagnostics.append(Diagnostic("bundle.row_required", f"{label} is missing `{field}`."))
        elif not _matches_type(value[field], expected):
            diagnostics.append(Diagnostic("bundle.row_type", f"{label}.{field} must be {expected}."))
    for field, expected in optional.items():
        if field in value and not _matches_type(value[field], expected):
            diagnostics.append(Diagnostic("bundle.row_type", f"{label}.{field} must be {expected}."))
    unknown = set(value) - set(required) - set(optional)
    if unknown:
        diagnostics.append(Diagnostic("bundle.row_unknown", f"{label} has unsupported fields: {', '.join(sorted(unknown))}."))
    return diagnostics


def _sha(value: object) -> bool:
    return isinstance(value, str) and (value == "" or re.fullmatch(r"[0-9a-f]{64}", value) is not None)


_LANGUAGE_SUFFIXES = {
    "python": {".py", ".pyi"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx", ".mts", ".cts"},
}


def _language_for_path(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    return next((language for language, suffixes in _LANGUAGE_SUFFIXES.items() if suffix in suffixes), None)


def _contains(path: Path, marker: str) -> bool:
    try:
        return marker in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _configured_quality_tools(repo_root: Path) -> dict[str, set[str]]:
    """Return only quality tools explicitly configured by repository files."""
    configured: dict[str, set[str]] = {language: set() for language in _LANGUAGE_SUFFIXES}
    pyproject = repo_root / "pyproject.toml"
    setup_cfg = repo_root / "setup.cfg"
    if (
        (repo_root / "ruff.toml").is_file()
        or (repo_root / ".ruff.toml").is_file()
        or _contains(pyproject, "[tool.ruff")
    ):
        configured["python"].add("ruff")
    if (
        (repo_root / "mypy.ini").is_file()
        or (repo_root / ".mypy.ini").is_file()
        or _contains(pyproject, "[tool.mypy")
        or _contains(setup_cfg, "[mypy")
    ):
        configured["python"].add("mypy")

    eslint_files = (
        ".eslintrc",
        ".eslintrc.json",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.yml",
        ".eslintrc.yaml",
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
    )
    package_json = repo_root / "package.json"
    eslint_configured = any((repo_root / name).is_file() for name in eslint_files) or _contains(
        package_json, '"eslintConfig"'
    )
    if eslint_configured:
        configured["javascript"].add("eslint")
        configured["typescript"].add("eslint")
    if (repo_root / "tsconfig.json").is_file():
        configured["typescript"].add("tsc")
    return configured


def _quality_row_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("tool", "")), str(row.get("command", ""))


def _quality_diagnostics(
    bundle: dict[str, Any], repo_root: Path, contract: dict[str, Any]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    rows = bundle["quality_checks"]
    baseline_rows = bundle["baseline"]["quality_checks"]
    touched: dict[str, set[str]] = {}
    for change in bundle["changes"]:
        for path in change["paths"]:
            language = _language_for_path(path)
            if language:
                touched.setdefault(language, set()).add(path)

    for index, row in enumerate(baseline_rows):
        diagnostics.extend(
            _row_diagnostics(row, "quality_check", f"baseline.quality_checks[{index}]", contract)
        )
    for index, row in enumerate(rows):
        diagnostics.extend(_row_diagnostics(row, "quality_check", f"quality_checks[{index}]", contract))
    if any(item.code.startswith("bundle.row_") for item in diagnostics):
        return diagnostics

    configured = _configured_quality_tools(repo_root)
    baseline_failures = {
        _quality_row_key(row)
        for row in baseline_rows
        if row["status"] == "failed" and row["exit_code"] != 0 and row["evidence"].strip()
    }
    for index, row in enumerate(rows):
        label = f"quality_checks[{index}]"
        sections = row["checklist_section"]
        if not sections or len(sections) != len(set(sections)) or not set(sections) <= {"1", "2", "3", "4"}:
            diagnostics.append(
                Diagnostic("bundle.quality_missing", f"{label}.checklist_section must cite sections 1-4.")
            )
        if not row["paths"] or set(row["file_sha256"]) != set(row["paths"]):
            diagnostics.append(
                Diagnostic("bundle.quality_stale", f"{label} hashes must exactly cover non-empty paths.")
            )
        for path in row["paths"]:
            language = _language_for_path(path)
            if language not in touched or path not in touched.get(language, set()):
                diagnostics.append(
                    Diagnostic("bundle.quality_stale", f"{label} covers an unchanged or unsupported path: {path}.")
                )
            digest = row["file_sha256"].get(path)
            if not _sha(digest) or digest != sha256_file(repo_root / path):
                diagnostics.append(
                    Diagnostic("bundle.quality_stale", f"{label} evidence is stale for {path}.")
                )
        if not row["evidence"].strip():
            diagnostics.append(Diagnostic("bundle.quality_missing", f"{label} requires non-empty evidence."))
        if row["status"] not in contract["verification_statuses"]:
            diagnostics.append(Diagnostic("bundle.quality_failed", f"{label}.status is unsupported."))
        elif row["status"] == "passed":
            if row["exit_code"] != 0:
                diagnostics.append(
                    Diagnostic("bundle.quality_failed", f"{label} passed status requires exit code zero.")
                )
        elif row["status"] == "skipped":
            diagnostics.append(
                Diagnostic("bundle.quality_tool_unavailable", f"{label} records unavailable quality tooling.")
            )
        elif not (
            row.get("classification") == "pre-existing-failure"
            and row["exit_code"] != 0
            and _quality_row_key(row) in baseline_failures
        ):
            diagnostics.append(
                Diagnostic("bundle.quality_failed", f"{label} is not a proven pre-existing failure.")
            )
        if "classification" in row and row["classification"] not in contract["quality_classifications"]:
            diagnostics.append(
                Diagnostic("bundle.quality_failed", f"{label}.classification is unsupported.")
            )

    for language, paths in touched.items():
        tools = configured.get(language, set())
        if not tools:
            unavailable = [
                row
                for row in rows
                if row["status"] == "skipped"
                and row["exit_code"] == 127
                and paths <= set(row["paths"])
            ]
            if not unavailable:
                diagnostics.append(
                    Diagnostic(
                        "bundle.quality_missing",
                        f"{language} changes require an evidenced skipped row because no quality tool is configured.",
                    )
                )
            continue
        for tool in sorted(tools):
            tool_rows = [row for row in rows if row["tool"] == tool]
            covered = {path for row in tool_rows for path in row["paths"]}
            if not tool_rows or not paths <= covered:
                diagnostics.append(
                    Diagnostic(
                        "bundle.quality_missing",
                        f"Configured {tool} evidence does not cover every touched {language} path.",
                    )
                )
    return diagnostics


def _implementation_binding_diagnostics(plan: Any, bundle: dict[str, Any], repo_root: Path) -> list[Diagnostic]:
    if not plan.binding:
        return []
    diagnostics: list[Diagnostic] = []
    state = repository_state(repo_root)
    if state["repository_id"] != plan.binding.get("repository_id"):
        diagnostics.append(Diagnostic("bundle.binding_repository_stale", "Current repository identity differs from the finalized binding."))
    baseline_targets = {
        item["path"]: item["before_sha256"] for item in bundle["baseline"]["targets"]
    }
    authorized_paths = {
        path
        for row in bundle["changes"]
        for path in row["paths"]
    }
    for category in BINDING_CATEGORIES:
        diagnostic_category = category.rstrip("s")
        for item in plan.binding.get(category, []):
            path = item.get("path", "")
            expected_sha = item.get("sha256", "")
            if path in authorized_paths:
                if baseline_targets.get(path) != expected_sha:
                    diagnostics.append(
                        Diagnostic(
                            f"bundle.binding_{diagnostic_category}_stale",
                            f"Authorized bound {category} path has a stale baseline: {path}.",
                        )
                    )
            elif sha256_file(repo_root / path) != expected_sha:
                diagnostics.append(
                    Diagnostic(
                        f"bundle.binding_{diagnostic_category}_stale",
                        f"Bound {category} path changed during implementation: {path}.",
                    )
                )
    return diagnostics


def validate_bundle(
    bundle: object, plan_text: str, repo_root: Path, *, require_receipt: bool = False
) -> list[Diagnostic]:
    if not isinstance(bundle, dict):
        return [Diagnostic("bundle.type", "Implementation bundle must be a JSON object.")]
    contract = load_contract()
    diagnostics: list[Diagnostic] = []
    plan_version = plan_contract_version(plan_text)
    accepted_versions = set(contract["supported_plan_contract_versions"]) | set(
        contract["deprecated_plan_contract_versions"]
    )
    if plan_version not in accepted_versions:
        diagnostics.append(
            Diagnostic("contract.unsupported", f"plan-contract version {plan_version!r} is not accepted.")
        )
    for field in contract["required_bundle_fields"]:
        if field not in bundle:
            diagnostics.append(Diagnostic("bundle.required", f"Bundle is missing required field `{field}`."))
    if bundle.get("schema_version") != contract["contract_version"]:
        diagnostics.append(Diagnostic("bundle.schema_version", f"schema_version must be {contract['contract_version']}."))
    if not isinstance(bundle.get("run_id"), str) or not bundle.get("run_id"):
        diagnostics.append(Diagnostic("bundle.run_id", "run_id must be a non-empty string."))
    if bundle.get("status") not in contract["statuses"]:
        diagnostics.append(Diagnostic("bundle.status", f"status must be one of: {', '.join(contract['statuses'])}."))
    for field in (
        "changes",
        "verification",
        "quality_checks",
        "warnings",
        "unresolved_changes",
        "unresolved_tests",
        "deviations",
        "residual_risks",
    ):
        if not isinstance(bundle.get(field), list):
            diagnostics.append(Diagnostic("bundle.type", f"{field} must be a list."))
    for field in ("plan", "workspace", "baseline", "final_workspace", "report"):
        schema_name = "plan" if field == "plan" else field.replace("_", "-")
        if schema_name == "final-workspace":
            schema_name = "final_workspace"
        diagnostics.extend(_row_diagnostics(bundle.get(field), schema_name, field, contract))

    plan, plan_diagnostics = parse_plan(plan_text)
    diagnostics.extend(plan_diagnostics)
    if plan is None:
        return diagnostics
    if not plan.receipt or not plan.binding:
        diagnostics.append(Diagnostic("bundle.plan_receipt", "Implementation requires a finalized v5 plan."))
    else:
        if plan.receipt.get("body") != plan_digest(plan_text):
            diagnostics.append(Diagnostic("bundle.binding_plan_body_stale", "Finalized plan body receipt is stale."))
        if plan.receipt.get("binding") != binding_digest(plan.binding):
            diagnostics.append(Diagnostic("bundle.binding_receipt_stale", "Finalized plan binding receipt is stale."))

    blocking = {"bundle.required", "bundle.type", "bundle.schema_version", "bundle.run_id", "bundle.status", "bundle.row_type", "bundle.row_required"}
    if any(item.code in blocking for item in diagnostics):
        return diagnostics
    plan_row = bundle["plan"]
    if plan_row["sha256"] != hashlib.sha256(plan_text.encode()).hexdigest():
        diagnostics.append(Diagnostic("bundle.plan_sha", "Bundle plan SHA does not match the exact plan text."))
    if plan_row["normalized"] != json.loads(json.dumps(plan.to_dict())):
        diagnostics.append(Diagnostic("bundle.plan_preservation", "Bundle must preserve every normalized v5 plan record."))
    if bundle["tier"] != plan.tier:
        diagnostics.append(Diagnostic("bundle.tier", "Bundle tier must match finalized plan metadata."))
    if plan.binding and bundle["workspace"]["repository_id"] != plan.binding.get("repository_id"):
        diagnostics.append(Diagnostic("bundle.repository", "Workspace repository identity must match the finalized plan binding."))

    for index, row in enumerate(bundle["workspace"]["targets"]):
        diagnostics.extend(_row_diagnostics(row, "target", f"workspace.targets[{index}]", contract))
    for index, row in enumerate(bundle["baseline"]["targets"]):
        diagnostics.extend(_row_diagnostics(row, "target", f"baseline.targets[{index}]", contract))
    for index, row in enumerate(bundle["changes"]):
        diagnostics.extend(_row_diagnostics(row, "change", f"changes[{index}]", contract))
    for index, row in enumerate(bundle["verification"]):
        diagnostics.extend(_row_diagnostics(row, "verification", f"verification[{index}]", contract))
    for index, row in enumerate(bundle["warnings"]):
        diagnostics.extend(_row_diagnostics(row, "warning", f"warnings[{index}]", contract))
    for index, row in enumerate(bundle["deviations"]):
        diagnostics.extend(_row_diagnostics(row, "deviation", f"deviations[{index}]", contract))
    if any(item.code.startswith("bundle.row_") for item in diagnostics):
        return diagnostics
    deprecated_warnings = [
        row for row in bundle["warnings"] if row["code"] == "bundle.plan_contract_deprecated"
    ]
    if any(row["severity"] != "warning" for row in bundle["warnings"]):
        diagnostics.append(Diagnostic("bundle.warning", "Bundle warnings must use warning severity."))
    if any(row["code"] != "bundle.plan_contract_deprecated" for row in bundle["warnings"]):
        diagnostics.append(Diagnostic("bundle.warning", "Bundle contains an unsupported warning code."))
    if plan_version in set(contract["deprecated_plan_contract_versions"]):
        if len(deprecated_warnings) != 1:
            diagnostics.append(
                Diagnostic(
                    "bundle.warning",
                    "Deprecated plan contracts require exactly one bundle.plan_contract_deprecated warning.",
                )
            )
    elif deprecated_warnings:
        diagnostics.append(
            Diagnostic("bundle.warning", "Current plan contracts must not claim deprecation.")
        )

    diagnostics.extend(_implementation_binding_diagnostics(plan, bundle, repo_root))
    diagnostics.extend(_quality_diagnostics(bundle, repo_root, contract))

    bound_targets = {
        item["path"]: item["sha256"]
        for item in plan.binding.get("targets", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    } if plan.binding else {}
    workspace_targets = {item["path"]: item for item in bundle["workspace"]["targets"]}
    declared_targets = {change.fields.get("path", ""): change for change in plan.records.get("CH", ())}
    if set(workspace_targets) != set(declared_targets):
        diagnostics.append(Diagnostic("bundle.targets", "Workspace targets must exactly match plan CH paths."))
    for path, change in declared_targets.items():
        target = workspace_targets.get(path, {})
        expected_before = bound_targets.get(path, "") if change.fields.get("status") == "existing" else ""
        if target.get("status") != change.fields.get("status") or target.get("before_sha256") != expected_before:
            diagnostics.append(Diagnostic("bundle.target_baseline", f"Target baseline does not match finalized binding: {path}."))
    if bundle["baseline"]["targets"] != bundle["workspace"]["targets"] or bundle["baseline"]["dirty"] != bundle["workspace"]["initial_dirty"]:
        diagnostics.append(Diagnostic("bundle.baseline", "Baseline targets and dirty state must preserve the scaffolded workspace."))

    changes_by_id = {record.id: record for record in plan.records.get("CH", ())}
    tests_by_id = {record.id: record for record in plan.records.get("T", ())}
    authorized_paths: set[str] = set()
    implemented_changes: set[str] = set()
    planned_change_counts: dict[str, int] = {}
    for index, row in enumerate(bundle["changes"]):
        label = f"changes[{index}]"
        if row["kind"] not in contract["change_kinds"]:
            diagnostics.append(Diagnostic("bundle.change_kind", f"{label}.kind is unsupported."))
        if not row["paths"] or set(row["before_sha256"]) != set(row["paths"]) or set(row["after_sha256"]) != set(row["paths"]):
            diagnostics.append(Diagnostic("bundle.change_paths", f"{label} hashes must exactly cover non-empty paths."))
        if not row["ch_ids"] or not set(row["ch_ids"]) <= set(changes_by_id):
            diagnostics.append(Diagnostic("bundle.change_ids", f"{label} must reference known CH records."))
        implemented_changes.update(row["ch_ids"])
        authorized_paths.update(row["paths"])
        for path in row["paths"]:
            if not _sha(row["before_sha256"].get(path)) or not _sha(row["after_sha256"].get(path)):
                diagnostics.append(Diagnostic("bundle.change_hash", f"{label} has an invalid SHA for {path}."))
            if row["after_sha256"].get(path) != sha256_file(repo_root / path):
                diagnostics.append(Diagnostic("bundle.change_hash", f"{label} after SHA is stale for {path}."))
        if row["kind"] == "planned":
            for change_id in row["ch_ids"]:
                planned_change_counts[change_id] = planned_change_counts.get(change_id, 0) + 1
            allowed = {changes_by_id[ident].fields.get("path", "") for ident in row["ch_ids"]}
            if not set(row["paths"]) <= allowed:
                diagnostics.append(Diagnostic("bundle.planned_paths", f"{label} contains a path not owned by its CH records."))
            for path in row["paths"]:
                if path in workspace_targets and row["before_sha256"].get(path) != workspace_targets[path]["before_sha256"]:
                    diagnostics.append(Diagnostic("bundle.change_hash", f"{label} before SHA does not match the target baseline."))
        else:
            flags = row.get("policy_flags")
            reason = row.get("reason")
            required_flags = contract["mechanical_propagation"]["required_flags"]
            if not isinstance(flags, dict) or set(flags) != set(required_flags) or not all(flags.values()):
                diagnostics.append(Diagnostic("bundle.mechanical_flags", f"{label} must affirm every mechanical-propagation flag."))
            if reason not in contract["mechanical_propagation"]["allowed_reasons"]:
                diagnostics.append(Diagnostic("bundle.mechanical_reason", f"{label} has an unsupported mechanical reason."))

    passed_tests: set[str] = set()
    passed_plan_rows = 0
    passed_regression_rows = 0
    for index, row in enumerate(bundle["verification"]):
        label = f"verification[{index}]"
        kind = row.get("kind", "plan-test")
        if kind not in contract["verification_kinds"]:
            diagnostics.append(Diagnostic("bundle.verification_kind", f"{label}.kind is unsupported."))
            continue
        if row["status"] not in contract["verification_statuses"]:
            diagnostics.append(Diagnostic("bundle.verification_status", f"{label}.status is unsupported."))
        if kind == "plan-test":
            if not row["t_ids"] or not set(row["t_ids"]) <= set(tests_by_id):
                diagnostics.append(Diagnostic("bundle.verification_ids", f"{label} must reference known T records."))
            for test_id in row["t_ids"]:
                if row["command"] != tests_by_id[test_id].fields.get("command"):
                    diagnostics.append(
                        Diagnostic("bundle.verification_command", f"{label} does not match {test_id}'s command.")
                    )
        elif row["t_ids"]:
            diagnostics.append(Diagnostic("bundle.verification_ids", f"{label} regression rows must not claim T records."))
        if row["status"] == "passed":
            if row["exit_code"] != 0:
                diagnostics.append(Diagnostic("bundle.verification_outcome", f"{label} passed status requires exit code zero."))
            elif kind == "regression":
                passed_regression_rows += 1
            else:
                passed_tests.update(row["t_ids"])
                passed_plan_rows += 1

    initial_dirty = bundle["workspace"]["initial_dirty"]
    for path, initial in initial_dirty.items():
        if (
            not isinstance(initial, dict)
            or set(initial) != {"status", "sha256"}
            or not isinstance(initial.get("status"), str)
            or not _sha(initial.get("sha256"))
        ):
            diagnostics.append(Diagnostic("bundle.dirty_schema", f"Dirty snapshot row is malformed: {path}."))
        elif initial.get("sha256") != sha256_file(repo_root / path):
            diagnostics.append(Diagnostic("bundle.dirty_preservation", f"Pre-existing dirty path changed: {path}."))
    actual_status = git_status(repo_root)
    actual_changed = set(actual_status) - set(initial_dirty)
    for path in sorted(actual_changed - authorized_paths):
        diagnostics.append(Diagnostic("bundle.unauthorized_path", f"Changed path is not authorized by a change row: {path}."))

    state = repository_state(repo_root)
    expected_final = {
        "git_head": state["git_head"],
        "status": state["status"],
        "changed_paths": sorted(state["status"]),
        "dirty": state["dirty"],
    }
    if bundle["final_workspace"] != expected_final:
        diagnostics.append(Diagnostic("bundle.final_workspace", "Final workspace does not match the actual repository."))

    unresolved_changes = set(item for item in bundle["unresolved_changes"] if isinstance(item, str))
    unresolved_tests = set(item for item in bundle["unresolved_tests"] if isinstance(item, str))
    if not unresolved_changes <= set(changes_by_id) or not unresolved_tests <= set(tests_by_id):
        diagnostics.append(Diagnostic("bundle.unresolved", "Unresolved records must reference known CH/T IDs."))
    if bundle["status"] == "complete":
        if bundle["tier"] == "tiny" and passed_plan_rows < 1:
            diagnostics.append(
                Diagnostic("bundle.tier_profile", "Tiny complete runs require one successful plan-test command.")
            )
        if bundle["tier"] in {"standard", "high-risk"}:
            if any(
                row["kind"] == "planned" and len(row["ch_ids"]) != 1
                for row in bundle["changes"]
            ) or any(planned_change_counts.get(change_id) != 1 for change_id in changes_by_id):
                diagnostics.append(
                    Diagnostic(
                        "bundle.tier_profile",
                        f"{bundle['tier']} complete runs require one independent planned change row per CH record.",
                    )
                )
            if passed_regression_rows < 1:
                diagnostics.append(
                    Diagnostic(
                        "bundle.tier_profile",
                        f"{bundle['tier']} complete runs require a distinct successful regression verification.",
                    )
                )
        if implemented_changes != set(changes_by_id) or unresolved_changes:
            diagnostics.append(Diagnostic("bundle.change_accounting", "Complete runs must implement every CH record."))
        if passed_tests != set(tests_by_id) or unresolved_tests:
            diagnostics.append(Diagnostic("bundle.test_accounting", "Complete runs require successful verification for every T record."))
        if not bundle["report"]["summary"].strip():
            diagnostics.append(Diagnostic("bundle.report", "Complete runs require a non-empty report summary."))

    receipt = bundle.get("validation_receipt")
    if receipt is not None and bundle.get("status") != "complete":
        diagnostics.append(Diagnostic("bundle.receipt_status", "Only a complete implementation bundle may carry a receipt."))
    if require_receipt:
        body = dict(bundle)
        body.pop("validation_receipt", None)
        expected = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if (
            not isinstance(receipt, dict)
            or receipt.get("implementation_contract") != 3
            or receipt.get("plan_contract") != plan_version
            or receipt.get("sha256") != expected
        ):
            diagnostics.append(Diagnostic("bundle.receipt", "Implementation receipt is missing or does not match the bundle."))
    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    diagnostics = validate_bundle(
        json.loads(args.bundle.read_text(encoding="utf-8")),
        args.plan.read_text(encoding="utf-8"),
        args.repo_root,
    )
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": [item.to_dict() for item in diagnostics]}, indent=2))
    else:
        for item in diagnostics:
            print(item)
    return int(bool(diagnostics))


if __name__ == "__main__":
    raise SystemExit(main())
