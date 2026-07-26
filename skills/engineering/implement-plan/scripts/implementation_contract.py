"""Strict v5 plan intake and implementation-contract v3 scaffolding."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from plan_runtime import Diagnostic, Plan, validate_plan
from plan_runtime import parse_plan as _parse_plan


def load_contract() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "references" / "implementation-contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_version") != 3 or contract.get("supported_plan_contract_versions") != [5]:
        raise ValueError("implementation contract must be v3 and support only plan-contract v5")
    return contract


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


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


def validate_v5_repository_binding(text: str, root: Path) -> list[Diagnostic]:
    _, diagnostics = validate_plan(text, root, require_finalized=True)
    return diagnostics


def scaffold_bundle(repo_root: Path, plan_path: Path, output_path: Path, run_id: str) -> dict[str, Any]:
    text = plan_path.read_text(encoding="utf-8")
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
    return {
        "schema_version": load_contract()["contract_version"],
        "run_id": run_id,
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
        "baseline": {"targets": targets, "dirty": state["dirty"], "verification": []},
        "changes": [],
        "verification": [],
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
