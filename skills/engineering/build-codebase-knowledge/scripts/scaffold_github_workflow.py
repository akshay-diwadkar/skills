#!/usr/bin/env python3
"""Create an explicitly requested managed knowledge-refresh GitHub workflow."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BEGIN = "# BEGIN BUILD-CODEBASE-KNOWLEDGE WORKFLOW"
END = "# END BUILD-CODEBASE-KNOWLEDGE WORKFLOW"
DEFAULT_REPOSITORY = "akshay-diwadkar/skills"
DEFAULT_RUNTIME_DIR = ".codebase-knowledge-runtime"
DEFAULT_BRANCH = "main"


def _safe_relative_path(value: str, field: str) -> str:
    path = Path(value)
    if not value or any(ord(char) < 32 for char in value) or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a non-empty safe relative path")
    return path.as_posix()


def _validate_inputs(branch: str, repository: str, revision: str, runtime_dir: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("repository must be owner/name without whitespace, URLs, shell syntax, or traversal")
    if not branch or any(ord(char) < 32 for char in branch):
        raise ValueError("branch must be non-empty and contain no control characters")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be a 40-character lowercase commit SHA")
    return _safe_relative_path(runtime_dir, "runtime_dir")


def _workflow_block(branch: str, repository: str, revision: str, runtime_dir: str) -> str:
    runtime_dir = _validate_inputs(branch, repository, revision, runtime_dir)
    branch_yaml = json.dumps(branch)
    repository_yaml = json.dumps(repository)
    revision_yaml = json.dumps(revision)
    runtime_yaml = json.dumps(runtime_dir)
    cli_path = f"{runtime_dir}/skills/engineering/build-codebase-knowledge/scripts/cli.py"
    return f"""{BEGIN}
name: Refresh Codebase Knowledge
on:
  push:
    branches: [{branch_yaml}]
    paths-ignore: ['.agent/knowledge/**', 'AGENTS.md', 'CLAUDE.md']
permissions:
  contents: write
jobs:
  refresh-knowledge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: actions/setup-python@39cd14742d08025d69697f4a05358f6232772233 # v5.0.0
        with: {{python-version: '3.11'}}
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
        with:
          repository: {repository_yaml}
          ref: {revision_yaml}
          path: {runtime_yaml}
      - name: Refresh knowledge from repository changes
        run: |
          python {json.dumps(cli_path)} status --repo-root . --format json
          python {json.dumps(cli_path)} refresh --repo-root .
      - uses: stefanzweifel/git-auto-commit-action@e588668b8d28edb50e6afef614df8acdbf115f23 # v5.0.0
        with:
          commit_message: "docs(knowledge): auto-refresh codebase knowledge [skip ci]"
          file_pattern: ".agent/knowledge/**"
{END}
"""


def scaffold_github_workflow(
    repo_root: Path | str,
    *,
    revision: str,
    branch: str = DEFAULT_BRANCH,
    repository: str = DEFAULT_REPOSITORY,
    runtime_dir: str = DEFAULT_RUNTIME_DIR,
    workflow_file: Path | str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Create or update only an explicitly requested managed workflow."""
    root = Path(repo_root).resolve()
    raw_target = Path(workflow_file) if workflow_file else Path(".github/workflows/refresh-codebase-knowledge.yml")
    target = raw_target.resolve() if raw_target.is_absolute() else (root / raw_target).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("output workflow path must be inside repo_root") from exc
    block = _workflow_block(branch, repository, revision, runtime_dir)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        managed = BEGIN in existing and END in existing
        if not managed and not force:
            return {"status": "warning", "path": str(target), "message": "User-owned workflow was not overwritten."}
        if managed and not force:
            start = existing.index(BEGIN)
            end = existing.index(END) + len(END)
            updated = existing[:start] + block.rstrip() + existing[end:]
        else:
            updated = block
        if updated == existing:
            return {"status": "unchanged", "path": str(target)}
        target.write_text(updated, encoding="utf-8")
        return {"status": "updated", "path": str(target), "force": force}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(block, encoding="utf-8")
    return {"status": "created", "path": str(target), "force": force}
