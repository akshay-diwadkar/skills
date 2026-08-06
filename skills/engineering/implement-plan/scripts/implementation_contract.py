"""Versioned plan intake and implementation-contract v4 scaffolding."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from difflib import unified_diff
from pathlib import Path
from typing import Any

import plan_v6_runtime
import plan_v7_runtime

Diagnostic = plan_v7_runtime.Diagnostic
Plan = Any


def _runtime_for_version(version: int | None):
    if version == 6:
        return plan_v6_runtime
    if version == 7:
        return plan_v7_runtime
    return None


def load_contract() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "references" / "implementation-contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    supported = contract.get("supported_plan_contract_versions")
    deprecated = contract.get("deprecated_plan_contract_versions", [])
    if contract.get("contract_version") != 4:
        raise ValueError("implementation contract must be v4")
    if (
        not isinstance(supported, list)
        or not supported
        or not all(isinstance(version, int) and version > 0 for version in supported)
        or len(supported) != len(set(supported))
    ):
        raise ValueError("supported_plan_contract_versions must be a unique non-empty integer list")
    if (
        not isinstance(deprecated, list)
        or not all(isinstance(version, int) and version > 0 for version in deprecated)
        or len(deprecated) != len(set(deprecated))
        or set(supported) & set(deprecated)
    ):
        raise ValueError("deprecated_plan_contract_versions must be a unique disjoint integer list")
    return contract


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _snapshot_path(output_path: Path, repo_path: str) -> Path:
    name = hashlib.sha256(repo_path.encode("utf-8")).hexdigest() + ".before"
    return output_path.parent / "snapshots" / name


def _write_before_snapshots(repo_root: Path, output_path: Path, paths: list[str]) -> None:
    snapshot_dir = output_path.parent / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for repo_path in paths:
        source = repo_root / repo_path
        if not source.is_file():
            continue
        content = source.read_bytes()
        snapshot = _snapshot_path(output_path, repo_path)
        if snapshot.exists():
            if snapshot.read_bytes() != content:
                raise ValueError(f"before snapshot already exists with different content: {repo_path}")
            continue
        snapshot.write_bytes(content)


def read_before_snapshot_sha256(bundle_path: Path, repo_path: str) -> str:
    snapshot = _snapshot_path(bundle_path, repo_path)
    return sha256_file(snapshot) if snapshot.is_file() else ""


def unified_diff_for_change(
    repo_root: Path, bundle_path: Path, change: dict[str, Any]
) -> str:
    """Build review-only diff metadata after authoritative hashes are recorded."""
    paths = change.get("paths")
    before_hashes = change.get("before_sha256")
    after_hashes = change.get("after_sha256")
    if (
        not isinstance(paths, list)
        or not all(isinstance(path, str) for path in paths)
        or not isinstance(before_hashes, dict)
        or not isinstance(after_hashes, dict)
        or set(paths) != set(before_hashes)
        or set(paths) != set(after_hashes)
    ):
        raise ValueError("change paths and hash maps must exactly agree before generating a diff")
    chunks: list[str] = []
    for repo_path in paths:
        snapshot = _snapshot_path(bundle_path, repo_path)
        if not snapshot.is_file():
            raise ValueError(f"missing before snapshot: {repo_path}")
        before_bytes = snapshot.read_bytes()
        expected_before = before_hashes[repo_path]
        actual_before = hashlib.sha256(before_bytes).hexdigest()
        if expected_before not in {"", actual_before} or (expected_before == "" and before_bytes):
            raise ValueError(f"before snapshot hash mismatch: {repo_path}")
        target = repo_root / repo_path
        after_bytes = target.read_bytes() if target.is_file() else b""
        actual_after = hashlib.sha256(after_bytes).hexdigest() if target.is_file() else ""
        if after_hashes[repo_path] != actual_after:
            raise ValueError(f"after hash mismatch: {repo_path}")
        try:
            before_text = before_bytes.decode("utf-8").splitlines()
            after_text = after_bytes.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            chunks.append(f"Binary files a/{repo_path} and b/{repo_path} differ\n")
            continue
        lines = unified_diff(
            before_text,
            after_text,
            fromfile=f"a/{repo_path}",
            tofile=f"b/{repo_path}",
            lineterm="",
        )
        diff = "\n".join(lines)
        if diff:
            chunks.append(diff + "\n")
    return "".join(chunks)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def git_status(root: Path, paths: list[str]) -> dict[str, str]:
    """Inspect only plan-selected paths; never snapshot a whole worktree."""
    status: dict[str, str] = {}
    for path in paths:
        result = _git(root, "status", "--porcelain=v1", "--", path)
        for line in result.stdout.splitlines():
            if len(line) > 3:
                status[line[3:].rsplit(" -> ", 1)[-1].replace("\\", "/")] = line[:2]
    return status


def dirty_snapshot(root: Path, paths: list[str]) -> dict[str, dict[str, str]]:
    return {
        path: {"status": status, "sha256": sha256_file(root / path)}
        for path, status in git_status(root, paths).items()
    }


def repository_state(root: Path, paths: list[str]) -> dict[str, Any]:
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    is_git = inside.returncode == 0 and inside.stdout.strip() == "true"
    head = _git(root, "rev-parse", "HEAD").stdout.strip() if is_git else ""
    branch = _git(root, "branch", "--show-current").stdout.strip() if is_git else ""
    remote = _git(root, "config", "--get", "remote.origin.url").stdout.strip() if is_git else ""
    return {
        "repository_id": remote or str(root.resolve()),
        "git_head": head or None,
        "branch": branch or None,
        "status": git_status(root, paths),
        "dirty": dirty_snapshot(root, paths),
    }


def parse_plan(text: str) -> tuple[Plan | None, list[Any]]:
    version = plan_contract_version(text)
    runtime = _runtime_for_version(version)
    if runtime is None:
        return None, [
            Diagnostic(
                "contract.unsupported",
                f"plan-contract version {version!r} is not supported",
                "Use a sealed plan-contract v6 or v7 plan.",
            )
        ]
    plan, diagnostics = runtime.parse_plan(runtime.canonical_body(text))
    proof_matches = list(runtime.PROOF_RE.finditer(text))
    receipt_matches = list(runtime.VALIDATION_RE.finditer(text))
    if plan is not None and len(proof_matches) == 1 and len(receipt_matches) == 1:
        try:
            proof = json.loads(proof_matches[0].group("json"))
            binding = proof.get("binding") if isinstance(proof, dict) else None
            if isinstance(binding, dict):
                plan = __import__("dataclasses").replace(
                    plan,
                    binding=binding,
                    receipt={
                        "body": receipt_matches[0].group("body"),
                        "proof": receipt_matches[0].group("proof"),
                    },
                )
        except json.JSONDecodeError:
            pass
    return plan, diagnostics


def plan_contract_version(text: str) -> int | None:
    matches = re.findall(r"<!--\s*plan-contract:\s*(\d+)\s*-->", text)
    return int(matches[0]) if len(matches) == 1 else None


def change_order_for_plan(plan: Plan, version: int | None) -> list[str]:
    if version == 7:
        ordered, diagnostics = plan_v7_runtime.topological_change_order(plan)
        if diagnostics:
            raise ValueError("invalid change dependency order:\n" + "\n".join(str(item) for item in diagnostics))
        return ordered
    return [record.id for record in plan.records.get("CH", ())]


def _depends_on_raw(plan: Plan, ch_id: str, version: int | None) -> str:
    if version != 7:
        return "none"
    for record in plan.records.get("CH", ()):
        if record.id == ch_id:
            return record.fields.get("depends_on", "none")
    return "none"


def _depends_on_ids(raw: str) -> set[str]:
    text = (raw or "").strip()
    if not text or text == "none":
        return set()
    return {part.strip() for part in text.split(",") if part.strip()}


def _refs(value: str) -> set[str]:
    return set(plan_v7_runtime.ID_RE.findall(value))


def validate_bundle_against_plan(
    bundle: dict[str, Any],
    plan: Plan,
    plan_text: str,
    version: int | None,
    *,
    require_completion: bool = True,
    repo_root: Path | None = None,
    bundle_path: Path | None = None,
) -> list[str]:
    """Return human-readable errors when order or completion sequencing is invalid."""
    errors: list[str] = []
    expected_order = change_order_for_plan(plan, version)
    plan_block = bundle.get("plan")
    workspace = bundle.get("workspace")
    if not isinstance(plan_block, dict):
        errors.append("bundle.plan must be an object with contract_version and change_order")
        return errors
    if not isinstance(workspace, dict):
        errors.append("bundle.workspace must be an object with change_order and targets")
        return errors
    if plan_block.get("contract_version") != version:
        errors.append(
            f"bundle.plan.contract_version must equal sealed plan version {version!r}"
        )
    plan_order = plan_block.get("change_order")
    workspace_order = workspace.get("change_order")
    if plan_order != expected_order:
        errors.append("bundle.plan.change_order must equal sealed plan dependency order")
    if workspace_order != expected_order:
        errors.append("bundle.workspace.change_order must equal sealed plan dependency order")
    if plan_order != workspace_order:
        errors.append("bundle.plan.change_order must equal bundle.workspace.change_order")
    expected_sha = hashlib.sha256(plan_text.encode()).hexdigest()
    if plan_block.get("sha256") != expected_sha:
        errors.append("bundle.plan.sha256 must match the sealed plan bytes")
    targets = workspace.get("targets")
    if not isinstance(targets, list):
        errors.append("bundle.workspace.targets must be an array")
        return errors
    if [target.get("ch_id") for target in targets if isinstance(target, dict)] != expected_order:
        errors.append("bundle.workspace.targets must follow change_order exactly")
    changes_by_id = {record.id: record for record in plan.records.get("CH", ())}
    tests_by_id = {record.id: record for record in plan.records.get("T", ())}
    targets_by_ch: dict[str, dict[str, Any]] = {}
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"workspace.targets[{index}] must be an object")
            continue
        ch_id = target.get("ch_id")
        if not isinstance(ch_id, str) or ch_id not in changes_by_id:
            errors.append(f"workspace.targets[{index}].ch_id is not a planned CH")
            continue
        targets_by_ch[ch_id] = target
        change = changes_by_id[ch_id]
        expected_depends = _depends_on_raw(plan, ch_id, version)
        if target.get("depends_on") != expected_depends:
            errors.append(f"workspace.targets[{index}].depends_on must match {ch_id}")
        target_path = change.fields.get("path", "")
        if target.get("path") != target_path:
            errors.append(f"workspace.targets[{index}].path must match {ch_id}")
        if bundle_path is not None and target_path:
            expected_before: str | None = None
            if target.get("status") == "new":
                expected_before = ""
            else:
                expected_before = read_before_snapshot_sha256(bundle_path, target_path)
                if not expected_before:
                    errors.append(
                        f"workspace.targets[{index}] before snapshot is missing for {target_path}"
                    )
                    expected_before = None
            if expected_before is not None and target.get("before_sha256") != expected_before:
                errors.append(
                    f"workspace.targets[{index}].before_sha256 must match scaffolded before snapshot for {target_path}"
                )
        for field in ("locality", "reversibility"):
            expected = change.fields.get(field, "") if version == 7 else change.fields.get(field, "")
            if version == 7 and target.get(field) != expected:
                errors.append(f"workspace.targets[{index}].{field} must match {ch_id}")
    completed: set[str] = set()
    completed_ch_ids: list[str] = []
    changes = bundle.get("changes", [])
    if not isinstance(changes, list):
        errors.append("bundle.changes must be an array")
        changes = []
    for index, change_row in enumerate(changes):
        if not isinstance(change_row, dict):
            errors.append(f"changes[{index}] must be an object")
            continue
        ch_ids = change_row.get("ch_ids")
        if not isinstance(ch_ids, list) or not all(isinstance(item, str) for item in ch_ids):
            errors.append(f"changes[{index}].ch_ids must be a string array")
            continue
        if require_completion:
            paths = change_row.get("paths")
            anchors = change_row.get("anchors")
            before_hashes = change_row.get("before_sha256")
            after_hashes = change_row.get("after_sha256")
            evidence = change_row.get("evidence")
            if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
                errors.append(f"changes[{index}].paths must be a string array")
            elif not isinstance(anchors, list) or not all(isinstance(item, str) for item in anchors):
                errors.append(f"changes[{index}].anchors must be a string array")
            elif not isinstance(before_hashes, dict) or not isinstance(after_hashes, dict):
                errors.append(f"changes[{index}] must include before_sha256 and after_sha256 objects")
            elif not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
                errors.append(f"changes[{index}].evidence must be a string array")
            elif (
                set(paths) != set(before_hashes.keys())
                or set(paths) != set(after_hashes.keys())
                or len(paths) != len(before_hashes)
                or len(paths) != len(after_hashes)
            ):
                errors.append(
                    f"changes[{index}] paths, before_sha256, and after_sha256 must have identical path keys"
                )
            else:
                expected_paths = {
                    changes_by_id[ch_id].fields.get("path", "")
                    for ch_id in ch_ids
                    if ch_id in changes_by_id
                }
                expected_paths.discard("")
                if set(paths) != expected_paths:
                    errors.append(
                        f"changes[{index}].paths must equal planned paths for {', '.join(ch_ids)}"
                    )
                for ch_id in ch_ids:
                    if ch_id not in changes_by_id:
                        continue
                    change_record = changes_by_id[ch_id]
                    anchor = change_record.fields.get("anchor", "")
                    if anchor and anchor not in anchors:
                        errors.append(f"changes[{index}].anchors must include {ch_id} anchor")
                    required_evidence = _refs(change_record.fields.get("evidence", ""))
                    if required_evidence and not required_evidence.issubset(set(evidence)):
                        errors.append(f"changes[{index}].evidence must include {ch_id} evidence refs")
                    path = change_record.fields.get("path", "")
                    if not path:
                        continue
                    target = targets_by_ch.get(ch_id)
                    status = change_record.fields.get("status", "existing")
                    expected_before = None
                    if bundle_path is not None:
                        if status == "new":
                            expected_before = ""
                        else:
                            expected_before = read_before_snapshot_sha256(bundle_path, path)
                            if not expected_before:
                                errors.append(
                                    f"changes[{index}] before snapshot is missing for {path}"
                                )
                                expected_before = None
                    elif isinstance(target, dict):
                        expected_before = target.get("before_sha256")
                    if expected_before is not None and before_hashes.get(path) != expected_before:
                        errors.append(
                            f"changes[{index}].before_sha256[{path}] must match scaffolded {ch_id}"
                        )
                    reported_after = after_hashes.get(path, "")
                    if repo_root is not None:
                        actual_after = sha256_file(repo_root / path)
                        if reported_after != actual_after:
                            errors.append(
                                f"changes[{index}].after_sha256[{path}] must match current repository hash"
                            )
                    status = change_record.fields.get("status", "existing")
                    change_text = change_record.fields.get("change", "").strip()
                    before_value = before_hashes.get(path, "")
                    after_value = after_hashes.get(path, "")
                    if status == "new":
                        if not after_value:
                            errors.append(f"changes[{index}] must record a non-empty after hash for new {ch_id}")
                    elif change_text and before_value == after_value:
                        errors.append(
                            f"changes[{index}] must record a real file change for planned behavioral {ch_id}"
                        )
        for ch_id in ch_ids:
            if ch_id not in changes_by_id:
                errors.append(f"changes[{index}] references unknown CH {ch_id}")
            deps = _depends_on_ids(_depends_on_raw(plan, ch_id, version))
            missing = sorted(deps - completed)
            if missing:
                errors.append(
                    f"changes[{index}] completes {ch_id} before prerequisites {', '.join(missing)}"
                )
            completed.add(ch_id)
            completed_ch_ids.append(ch_id)
    if require_completion:
        planned_ids = set(expected_order)
        completed_set = set(completed_ch_ids)
        if len(completed_ch_ids) != len(completed_set):
            errors.append("changes[].ch_ids must complete every planned CH exactly once")
        elif completed_set != planned_ids:
            errors.append("changes[].ch_ids must complete every planned CH exactly once")
        planned_tests = [record.id for record in plan.records.get("T", ())]
        planned_test_set = set(planned_tests)
        passed_tests: set[str] = set()
        verification = bundle.get("verification", [])
        if not isinstance(verification, list):
            errors.append("bundle.verification must be an array")
            verification = []
        for index, row in enumerate(verification):
            if not isinstance(row, dict):
                errors.append(f"verification[{index}] must be an object")
                continue
            t_ids = row.get("t_ids")
            if not isinstance(t_ids, list) or not all(isinstance(item, str) for item in t_ids):
                errors.append(f"verification[{index}].t_ids must be a string array")
                continue
            status = row.get("status")
            if status == "passed" and row.get("exit_code") != 0:
                errors.append(f"verification[{index}] with status passed must have exit_code 0")
            command = str(row.get("command", "")).strip()
            for t_id in t_ids:
                if t_id not in planned_test_set:
                    errors.append(f"verification[{index}] references unknown T {t_id}")
                elif status == "passed":
                    passed_tests.add(t_id)
                    planned = tests_by_id.get(t_id)
                    if planned is not None:
                        planned_command = str(planned.fields.get("command", "")).strip()
                        if command != planned_command:
                            errors.append(
                                f"verification[{index}].command must match planned {t_id}.command"
                            )
        missing_tests = sorted(planned_test_set - passed_tests)
        if missing_tests:
            errors.append(
                "every planned T must appear in a passed verification row: "
                + ", ".join(missing_tests)
            )
        if bundle.get("unresolved_changes") != []:
            errors.append("unresolved_changes must be empty to seal complete")
        if bundle.get("unresolved_tests") != []:
            errors.append("unresolved_tests must be empty to seal complete")
    return errors


def validate_plan_text(text: str, root: Path) -> tuple[Plan | None, list[Any]]:
    version = plan_contract_version(text)
    runtime = _runtime_for_version(version)
    if runtime is None:
        return None, [
            Diagnostic(
                "contract.unsupported",
                f"plan-contract version {version!r} is not supported",
                "Use a sealed plan-contract v6 or v7 plan.",
            )
        ]
    plan, diagnostics, _view = runtime.verify_sealed_plan(text, root)
    return plan, diagnostics


def validate_plan_for_completion(text: str) -> tuple[Plan | None, list[Any]]:
    """Validate sealed-plan markers and parse records without re-checking live evidence paths."""
    version = plan_contract_version(text)
    runtime = _runtime_for_version(version)
    if runtime is None:
        return None, [
            Diagnostic(
                "contract.unsupported",
                f"plan-contract version {version!r} is not supported",
                "Use a sealed plan-contract v6 or v7 plan.",
            )
        ]
    diagnostics: list[Any] = []
    proof_matches = list(runtime.PROOF_RE.finditer(text))
    receipt_matches = list(runtime.VALIDATION_RE.finditer(text))
    if len(proof_matches) != 1 or len(receipt_matches) != 1:
        diagnostics.append(
            Diagnostic(
                "proof.stale",
                "Sealed proof or receipt marker is missing.",
                "Use the exact output from seal_plan.py.",
                category="stale_evidence",
            )
        )
        return None, diagnostics
    body = runtime.canonical_body(text)
    try:
        proof = json.loads(proof_matches[0].group("json"))
        if not isinstance(proof, dict):
            raise ValueError("plan proof must be an object")
    except (json.JSONDecodeError, ValueError):
        diagnostics.append(
            Diagnostic(
                "proof.stale",
                "Plan proof is malformed.",
                "Use the exact output from seal_plan.py.",
                category="stale_evidence",
            )
        )
        return None, diagnostics
    receipt = receipt_matches[0]
    body_digest = hashlib.sha256(body.encode()).hexdigest()
    proof_digest = hashlib.sha256(runtime._canonical_json(proof).encode()).hexdigest()
    if receipt.group("body") != body_digest or receipt.group("proof") != proof_digest:
        diagnostics.append(
            Diagnostic(
                "proof.stale",
                "Plan body or proof digest does not match the receipt.",
                "Reseal the unchanged draft.",
                category="stale_evidence",
            )
        )
    plan, parse_diagnostics = runtime.parse_plan(body)
    diagnostics.extend(parse_diagnostics)
    if plan is None:
        return None, diagnostics
    return plan, diagnostics


def scaffold_bundle(repo_root: Path, plan_path: Path, output_path: Path, run_id: str) -> dict[str, Any]:
    text = plan_path.read_text(encoding="utf-8")
    contract = load_contract()
    version = plan_contract_version(text)
    supported = set(contract["supported_plan_contract_versions"])
    if version not in supported:
        raise ValueError(
            f"contract.unsupported: plan-contract version {version!r} is not supported or deprecated"
        )
    plan, diagnostics = validate_plan_text(text, repo_root)
    if diagnostics or plan is None:
        raise ValueError("invalid plan:\n" + "\n".join(str(item) for item in diagnostics))
    if output_path.is_relative_to(repo_root) and not (repo_root / ".gitignore").is_file():
        raise ValueError("output must be outside the repository or ignored")
    change_order = change_order_for_plan(plan, version)
    changes_by_id = {record.id: record for record in plan.records.get("CH", ())}
    ordered_changes = [changes_by_id[identifier] for identifier in change_order if identifier in changes_by_id]
    targets = [
        {
            "path": change.fields.get("path", ""),
            "status": change.fields.get("status", ""),
            "before_sha256": sha256_file(repo_root / change.fields.get("path", "")),
            "ch_id": change.id,
            "depends_on": change.fields.get("depends_on", "none") if version == 7 else "none",
            "locality": change.fields.get("locality", ""),
            "reversibility": change.fields.get("reversibility", ""),
        }
        for change in ordered_changes
    ]
    target_paths = [target["path"] for target in targets if target["path"]]
    state = repository_state(repo_root, target_paths)
    _write_before_snapshots(repo_root, output_path, [target["path"] for target in targets])
    return {
        "schema_version": contract["contract_version"],
        "run_id": run_id,
        "tier": plan.tier,
        "status": "in-progress",
        "plan": {
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "normalized": json.loads(json.dumps(plan.to_dict())),
            "contract_version": version,
            "change_order": change_order,
        },
        "workspace": {
            "repository_id": state["repository_id"],
            "git_head": state["git_head"],
            "branch": state["branch"],
            "targets": targets,
            "change_order": change_order,
            "initial_dirty": state["dirty"],
        },
        "baseline": {
            "targets": targets,
            "dirty": state["dirty"],
            "verification": [],
            "quality_checks": [],
        },
        "changes": [],
        "verification": [],
        "quality_checks": [],
        "warnings": (
            []
        ),
        "unresolved_changes": [],
        "unresolved_tests": [],
        "deviations": [],
        "final_workspace": {
            "git_head": state["git_head"],
            "status": state["status"],
            "changed_paths": sorted(state["status"]),
            "dirty": state["dirty"],
        },
        "residual_risks": [],
        "report": {"summary": ""},
    }
