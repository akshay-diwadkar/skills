#!/usr/bin/env python3
"""Link generated knowledge docs inside AGENTS.md and CLAUDE.md using managed HTML comment blocks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

MANAGED_BEGIN = "<!-- BEGIN BUILD-CODEBASE-KNOWLEDGE -->"
MANAGED_END = "<!-- END BUILD-CODEBASE-KNOWLEDGE -->"


def generate_managed_block(rel_k_path: str) -> str:
    """Generate HTML comment managed block content for agent documentation."""
    return f"""{MANAGED_BEGIN}
## Repository Knowledge
Repository knowledge is available under `{rel_k_path}/`. Before broad exploration: check freshness, resolve the current task, read phase 1 only, and expand only when its stop condition is unmet. Source remains authoritative; load maps and symbol shards selectively.
{MANAGED_END}"""


def update_file_with_managed_block(fpath: Path, rel_k_path: str) -> bool:
    """Update or append managed block in fpath. Returns True if file was modified."""
    content = fpath.read_text(encoding="utf-8")

    # Check opt-out marker
    if "<!-- OPT-OUT BUILD-CODEBASE-KNOWLEDGE -->" in content:
        return False

    new_block = generate_managed_block(rel_k_path)

    if MANAGED_BEGIN in content and MANAGED_END in content:
        start_idx = content.find(MANAGED_BEGIN)
        end_idx = content.find(MANAGED_END) + len(MANAGED_END)
        existing_block = content[start_idx:end_idx]

        if existing_block.strip() == new_block.strip():
            return False  # Already up to date

        new_content = content[:start_idx] + new_block + content[end_idx:]
    else:
        # Append managed block at end of file
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    fpath.write_text(new_content, encoding="utf-8")
    return True


def link_agent_docs(repo_root: Path | str, output_dir: Path | str | None = None, create_missing: bool = False) -> dict[str, Any]:
    """Link repository knowledge documentation in AGENTS.md / CLAUDE.md using managed blocks."""
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

    modified: list[str] = []
    created: list[str] = []

    def starter_template(title: str) -> str:
        return f"# {title}\n\n{generate_managed_block(rel_k_path)}\n"

    existing = [(agents_file, "AGENTS.md"), (claude_file, "CLAUDE.md")]
    for fpath, name in existing:
        if fpath.is_file():
            if update_file_with_managed_block(fpath, rel_k_path):
                modified.append(name)
    if not modified and not any(path.is_file() for path, _ in existing) and create_missing:
        agents_file.write_text(starter_template("AGENTS.md"), encoding="utf-8")
        created.append("AGENTS.md")

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
    parser.add_argument("--create-missing", action="store_true", help="Create AGENTS.md only when no supported instruction file exists")

    args = parser.parse_args()
    res = link_agent_docs(args.repo_root, args.output, args.create_missing)

    if res["created"]:
        print(f"Created agent doc files referencing '{res['knowledge_path']}': {', '.join(res['created'])}")
    elif res["modified"]:
        print(f"Updated agent doc files referencing '{res['knowledge_path']}': {', '.join(res['modified'])}")
    else:
        print("Agent doc files already up to date. No changes made.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
