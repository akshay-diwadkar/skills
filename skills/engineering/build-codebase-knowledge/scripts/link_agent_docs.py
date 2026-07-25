#!/usr/bin/env python3
"""Link generated knowledge docs inside AGENTS.md and CLAUDE.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def link_agent_docs(repo_root: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Link repository knowledge documentation in AGENTS.md / CLAUDE.md.
    
    Rules:
    1. If AGENTS.md or CLAUDE.md exists, adds a reference line to the knowledge docs folder (if not already present).
    2. If neither AGENTS.md nor CLAUDE.md exists, creates both with reference to the knowledge docs folder.
    """
    root = Path(repo_root).resolve()
    if output_dir:
        k_dir = Path(output_dir).resolve()
    else:
        k_dir = root / ".agent" / "knowledge"

    try:
        rel_k_path = k_dir.relative_to(root).as_posix()
    except ValueError:
        rel_k_path = k_dir.as_posix()

    agents_file = root / "AGENTS.md"
    claude_file = root / "CLAUDE.md"

    agents_exists = agents_file.is_file()
    claude_exists = claude_file.is_file()

    modified: list[str] = []
    created: list[str] = []

    ref_line_section = (
        f"\n\n## Repository Knowledge\n"
        f"- See [{rel_k_path}/]({rel_k_path}/) for codebase orientation and architecture overview.\n"
    )

    starter_template = lambda title: (
        f"# {title}\n\n"
        f"## Repository Knowledge\n"
        f"- Codebase orientation, component matrix, and entry points: [{rel_k_path}/context.md]({rel_k_path}/context.md)\n"
        f"- Architecture, dependencies, and risk points: [{rel_k_path}/architecture.md]({rel_k_path}/architecture.md)\n"
    )

    if agents_exists or claude_exists:
        for fpath, name in [(agents_file, "AGENTS.md"), (claude_file, "CLAUDE.md")]:
            if fpath.is_file():
                content = fpath.read_text(encoding="utf-8")
                # Idempotency check: avoid adding duplicate references
                if rel_k_path not in content and "context.md" not in content and "knowledge" not in content.lower():
                    new_content = content.rstrip() + ref_line_section
                    fpath.write_text(new_content, encoding="utf-8")
                    modified.append(name)
    else:
        agents_file.write_text(starter_template("AGENTS.md"), encoding="utf-8")
        created.append("AGENTS.md")

        claude_file.write_text(starter_template("CLAUDE.md"), encoding="utf-8")
        created.append("CLAUDE.md")

    return {
        "status": "success",
        "modified": modified,
        "created": created,
        "knowledge_path": rel_k_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Link repository knowledge docs in AGENTS.md / CLAUDE.md.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--output", help="Knowledge output directory")

    args = parser.parse_args()
    res = link_agent_docs(args.repo_root, args.output)

    if res["created"]:
        print(f"Created agent doc files referencing '{res['knowledge_path']}': {', '.join(res['created'])}")
    elif res["modified"]:
        print(f"Updated agent doc files referencing '{res['knowledge_path']}': {', '.join(res['modified'])}")
    else:
        print(f"Agent doc files already reference '{res['knowledge_path']}'. No changes made.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
