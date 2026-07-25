#!/usr/bin/env python3
"""Generate GitHub Action workflow file to auto-refresh codebase knowledge docs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def scaffold_github_workflow(
    repo_root: Path | str,
    branch: str = "main",
    workflow_file: Path | str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Scaffold a GitHub Action workflow to auto-refresh codebase knowledge docs on push."""
    root = Path(repo_root).resolve()

    if workflow_file:
        wf_path = Path(workflow_file).resolve()
    else:
        wf_path = root / ".github" / "workflows" / "refresh-codebase-knowledge.yml"

    if wf_path.exists() and not force:
        return {
            "status": "error",
            "message": f"Workflow file already exists at '{wf_path}'. Use --force to overwrite.",
            "path": str(wf_path),
        }

    wf_path.parent.mkdir(parents=True, exist_ok=True)

    workflow_content = f"""name: Refresh Codebase Knowledge

on:
  push:
    branches:
      - {branch}
    paths-ignore:
      - '.agent/knowledge/**'

jobs:
  refresh-knowledge:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build Codebase Knowledge & Link Agent Docs
        run: |
          python skills/engineering/build-codebase-knowledge/scripts/build_knowledge.py --repo-root .

      - name: Commit and Push Updated Knowledge Artifacts
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "docs(knowledge): auto-refresh codebase knowledge [skip ci]"
          file_pattern: ".agent/knowledge/* AGENTS.md CLAUDE.md"
"""

    wf_path.write_text(workflow_content, encoding="utf-8")

    try:
        rel_display = str(wf_path.relative_to(root))
    except ValueError:
        rel_display = str(wf_path)

    return {
        "status": "success",
        "path": rel_display,
        "branch": branch,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GitHub Action workflow file to auto-refresh codebase knowledge.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--branch", default="main", help="Target git branch (default: main)")
    parser.add_argument("--output", help="Custom output workflow file path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing workflow file")

    args = parser.parse_args()
    res = scaffold_github_workflow(args.repo_root, args.branch, args.output, args.force)

    if res["status"] == "error":
        print(f"Error: {res['message']}", file=sys.stderr)
        return 1

    print(f"Successfully generated GitHub Action workflow at '{res['path']}' for branch '{res['branch']}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
