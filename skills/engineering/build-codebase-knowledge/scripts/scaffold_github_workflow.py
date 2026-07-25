#!/usr/bin/env python3
"""Provision the managed knowledge-refresh GitHub Actions workflow."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

BEGIN = "# BEGIN BUILD-CODEBASE-KNOWLEDGE WORKFLOW"
END = "# END BUILD-CODEBASE-KNOWLEDGE WORKFLOW"

def _block(branch: str, repository: str, revision: str, runtime_dir: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("workflow runtime revision must be a 40-character lowercase commit SHA")
    return f'''{BEGIN}
name: Refresh Codebase Knowledge
on:
  push:
    branches: [{branch}]
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
          repository: akshay-diwadkar/skills
          ref: {revision}
          path: {runtime_dir}
      - run: python {runtime_dir}/skills/engineering/build-codebase-knowledge/scripts/cli.py build --repo-root .
      - uses: stefanzweifel/git-auto-commit-action@e588668b8d28edb50e6afef614df8acdbf115f23 # v5.0.0
        with:
          commit_message: "docs(knowledge): auto-refresh codebase knowledge [skip ci]"
          file_pattern: ".agent/knowledge/** AGENTS.md CLAUDE.md"
{END}
'''

def ensure_github_workflow(repo_root: Path | str, branch: str = "main", repository: str = "https://github.com/akshay-diwadkar/skills.git", revision: str = "09a44216123f4621a59ef965ccaa5aa96d3a2e5a", runtime_dir: str = ".codebase-knowledge-runtime") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = root / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    block = _block(branch, repository, revision, runtime_dir)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if BEGIN not in text or END not in text:
            return {"status": "warning", "path": str(path), "message": "User-owned workflow was not overwritten."}
        start, end = text.index(BEGIN), text.index(END) + len(END)
        updated = text[:start] + block.rstrip() + text[end:]
        if updated == text:
            return {"status": "unchanged", "path": str(path)}
        path.write_text(updated, encoding="utf-8")
        return {"status": "updated", "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(block, encoding="utf-8")
    return {"status": "created", "path": str(path)}

def scaffold_github_workflow(repo_root: Path | str, branch: str = "main", workflow_file: Path | str | None = None, mode: str = "cli", force: bool = False) -> dict[str, Any]:
    result = ensure_github_workflow(repo_root, branch)
    if workflow_file and result["status"] != "warning":
        target = Path(workflow_file).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_block(branch, "https://github.com/akshay-diwadkar/skills.git", "09a44216123f4621a59ef965ccaa5aa96d3a2e5a", ".codebase-knowledge-runtime"), encoding="utf-8")
        result["path"] = str(target)
    if result["status"] != "warning":
        result["status"] = "success"
        result["mode"] = mode
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()
    print(ensure_github_workflow(args.repo_root, args.branch))
