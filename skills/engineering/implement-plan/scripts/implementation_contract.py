"""Strict v5 plan intake and implementation-contract v3 scaffolding."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from difflib import unified_diff
from pathlib import Path
from typing import Any

from plan_runtime import Diagnostic, Plan, validate_plan
from plan_runtime import parse_plan as _parse_plan


def load_contract() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "references" / "implementation-contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    supported = contract.get("supported_plan_contract_versions")
    deprecated = contract.get("deprecated_plan_contract_versions")
    if contract.get("contract_version") != 3:
        raise ValueError("implementation contract must be v3")
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
        content = source.read_bytes() if source.is_file() else b""
        snapshot = _snapshot_path(output_path, repo_path)
        if snapshot.exists():
            if snapshot.read_bytes() != content:
                raise ValueError(f"before snapshot already exists with different content: {repo_path}")
            continue
        snapshot.write_bytes(content)


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


def git_status(root: Path) -> dict[str, str]:
    result = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        line[3:].rsplit(" -> ", 1)[-1].replace("\\", "/"): line[:2]
        for line in result.stdout.splitlines()
        if len(line) > 3
    }


def dirty_snapshot(root: Path) -> dict[str, dict[str, str]]:
    return {
        path: {"status": status, "sha256": sha256_file(root / path)}
        for path, status in git_status(root).items()
    }


def repository_state(root: Path) -> dict[str, Any]:
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    is_git = inside.returncode == 0 and inside.stdout.strip() == "true"
    head = _git(root, "rev-parse", "HEAD").stdout.strip() if is_git else ""
    branch = _git(root, "branch", "--show-current").stdout.strip() if is_git else ""
    remote = _git(root, "config", "--get", "remote.origin.url").stdout.strip() if is_git else ""
    return {
        "repository_id": remote or str(root.resolve()),
        "git_head": head or None,
        "branch": branch or None,
        "status": git_status(root),
        "dirty": dirty_snapshot(root),
    }


def parse_plan(text: str) -> tuple[Plan | None, list[Diagnostic]]:
    return _parse_plan(text)


def plan_contract_version(text: str) -> int | None:
    matches = re.findall(r"<!--\s*plan-contract:\s*(\d+)\s*-->", text)
    return int(matches[0]) if len(matches) == 1 else None


def validate_v5_repository_binding(text: str, root: Path) -> list[Diagnostic]:
    _, diagnostics = validate_plan(text, root, require_finalized=True)
    return diagnostics


def scaffold_bundle(repo_root: Path, plan_path: Path, output_path: Path, run_id: str) -> dict[str, Any]:
    text = plan_path.read_text(encoding="utf-8")
    contract = load_contract()
    version = plan_contract_version(text)
    supported = set(contract["supported_plan_contract_versions"])
    deprecated = set(contract["deprecated_plan_contract_versions"])
    if version not in supported | deprecated:
        raise ValueError(
            f"contract.unsupported: plan-contract version {version!r} is not supported or deprecated"
        )
    plan, diagnostics = validate_plan(text, repo_root, require_finalized=True)
    if diagnostics or plan is None:
        raise ValueError("invalid plan:\n" + "\n".join(str(item) for item in diagnostics))
    if output_path.is_relative_to(repo_root) and not (repo_root / ".gitignore").is_file():
        raise ValueError("output must be outside the repository or ignored")
    state = repository_state(repo_root)
    targets = [
        {
            "path": change.fields.get("path", ""),
            "status": change.fields.get("status", ""),
            "before_sha256": sha256_file(repo_root / change.fields.get("path", "")),
        }
        for change in plan.records.get("CH", ())
    ]
    _write_before_snapshots(repo_root, output_path, [target["path"] for target in targets])
    return {
        "schema_version": contract["contract_version"],
        "run_id": run_id,
        "tier": plan.tier,
        "status": "in-progress",
        "plan": {
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "normalized": json.loads(json.dumps(plan.to_dict())),
        },
        "workspace": {
            "repository_id": state["repository_id"],
            "git_head": state["git_head"],
            "branch": state["branch"],
            "targets": targets,
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
            [
                {
                    "code": "bundle.plan_contract_deprecated",
                    "severity": "warning",
                    "message": (
                        f"plan-contract v{version} is deprecated and will be removed after this release"
                    ),
                }
            ]
            if version in deprecated
            else []
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
