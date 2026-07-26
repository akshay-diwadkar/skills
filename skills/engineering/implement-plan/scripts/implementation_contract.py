"""v5 plan intake and implementation bundle scaffolding."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from plan_runtime import Diagnostic, Plan, validate_plan
from plan_runtime import parse_plan as _parse_plan


def load_contract() -> dict[str, Any]:
    return {"contract_version": 2, "statuses": ["in-progress", "complete", "partial", "blocked"]}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def git_status(root: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {line[3:].replace("\\", "/"): line[:2] for line in result.stdout.splitlines() if len(line) > 3}


def parse_plan(text: str) -> tuple[Plan | None, list[Diagnostic]]:
    return _parse_plan(text)


def validate_v5_repository_binding(text: str, root: Path) -> list[Diagnostic]:
    _, diagnostics = validate_plan(text, root, require_finalized=True)
    return diagnostics


def scaffold_bundle(repo_root: Path, plan_path: Path, output_path: Path, run_id: str) -> dict[str, Any]:
    text = plan_path.read_text(encoding="utf-8")
    plan, diagnostics = validate_plan(text, repo_root, require_finalized=True)
    if diagnostics or plan is None:
        raise ValueError("invalid plan:\n" + "\n".join(str(x) for x in diagnostics))
    if output_path.is_relative_to(repo_root) and not (repo_root / ".gitignore").is_file():
        raise ValueError("output must be outside the repository or ignored")
    return {
        "schema_version": 2,
        "run_id": run_id,
        "status": "in-progress",
        "plan": {"sha256": hashlib.sha256(text.encode()).hexdigest(), "normalized": plan.to_dict()},
        "workspace": {
            "targets": [
                {"path": x.fields.get("path"), "before_sha256": sha256_file(repo_root / x.fields.get("path", ""))}
                for x in plan.records.get("CH", ())
            ],
            "initial_dirty": git_status(repo_root),
        },
        "changes": [],
        "verification": [],
        "unresolved_changes": [],
        "unresolved_tests": [],
        "report": {"summary": ""},
    }
