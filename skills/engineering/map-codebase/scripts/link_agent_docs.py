#!/usr/bin/env python3
"""Maintain managed repository-knowledge references in agent instruction files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from knowledge.config import load_config, resolve_knowledge_directory

MANAGED_BEGIN = "<!-- BEGIN MAP-CODEBASE -->"
MANAGED_END = "<!-- END MAP-CODEBASE -->"
LEGACY_MANAGED_BEGIN = "<!-- BEGIN BUILD-CODEBASE-KNOWLEDGE -->"
LEGACY_MANAGED_END = "<!-- END BUILD-CODEBASE-KNOWLEDGE -->"
OPT_OUT = "<!-- OPT-OUT MAP-CODEBASE -->"


class AgentDocumentError(ValueError):
    """A supported instruction file has an unsafe managed-block state."""


def generate_managed_block(rel_k_path: str) -> str:
    """Generate the canonical repository-knowledge managed block."""
    return f"""{MANAGED_BEGIN}
## Repository Knowledge
Repository knowledge is available under `{rel_k_path}/`. Before broad exploration: check freshness, resolve the current task, read phase 1 only, and expand only when its stop condition is unmet. Source remains authoritative; load the repository map and only selected symbol shards.
{MANAGED_END}"""


def _marker_positions(content: str, marker: str) -> list[int]:
    positions: list[int] = []
    start = 0
    while (index := content.find(marker, start)) != -1:
        positions.append(index)
        start = index + len(marker)
    return positions


def _find_block(content: str, filename: str, begin: str, end: str, label: str) -> tuple[int, int] | None:
    begins = _marker_positions(content, begin)
    ends = _marker_positions(content, end)
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0] > ends[0]:
        raise AgentDocumentError(f"malformed {label} block in {filename}")
    return begins[0], ends[0] + len(end)


def _find_managed_block(content: str, filename: str) -> tuple[int, int] | None:
    """Return one valid canonical block, or a valid legacy block for migration."""
    canonical = _find_block(content, filename, MANAGED_BEGIN, MANAGED_END, "MAP-CODEBASE")
    legacy = _find_block(content, filename, LEGACY_MANAGED_BEGIN, LEGACY_MANAGED_END, "legacy MAP-CODEBASE")
    if canonical is not None and legacy is not None:
        raise AgentDocumentError(f"ambiguous MAP-CODEBASE blocks in {filename}")
    return canonical or legacy


def _newline_style(content: str) -> str:
    return "\r\n" if "\r\n" in content else "\n"


def _append_block(content: str, block: str, newline: str) -> str:
    if not content:
        return f"{block}{newline}"
    separator = newline if content.endswith(("\n", "\r")) else newline * 2
    return f"{content}{separator}{block}{newline}"


def _planned_content(path: Path, title: str, managed_block: str) -> tuple[str, str]:
    """Return the action and complete replacement text without writing the file."""
    if not path.exists():
        return "created", f"# {title}\n\n{managed_block}\n"
    if not path.is_file():
        raise AgentDocumentError(f"instruction path is not a file: {path.name}")

    content = path.read_bytes().decode("utf-8")
    if OPT_OUT in content:
        return "skipped", content

    newline = _newline_style(content)
    block = managed_block.replace("\n", newline)
    located = _find_managed_block(content, path.name)
    if located is None:
        final = _append_block(content, block, newline)
    else:
        start, end = located
        final = f"{content[:start]}{block}{content[end:]}"
    return ("unchanged" if final == content else "modified"), final


def _write_if_changed(path: Path, content: str) -> None:
    path.write_bytes(content.encode("utf-8"))


def ensure_agent_docs(repo_root: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Ensure both supported instruction files contain one current managed block."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    knowledge_dir = resolve_knowledge_directory(root, output_dir, config)
    rel_k_path = knowledge_dir.relative_to(root).as_posix()
    block = generate_managed_block(rel_k_path)
    targets = ((root / "AGENTS.md", "AGENTS.md"), (root / "CLAUDE.md", "CLAUDE.md"))

    # Plan and validate both targets before changing either one.
    planned = [(path, name, *_planned_content(path, name, block)) for path, name in targets]
    result: dict[str, Any] = {
        "status": "success",
        "created": [],
        "modified": [],
        "unchanged": [],
        "skipped": [],
        "knowledge_path": rel_k_path,
    }
    for path, name, action, content in planned:
        if action in {"created", "modified"}:
            _write_if_changed(path, content)
        result[action].append(name)
    return result


def link_agent_docs(
    repo_root: Path | str,
    output_dir: Path | str | None = None,
    create_missing: bool = False,
) -> dict[str, Any]:
    """Compatibility wrapper; missing supported instruction files are always created."""
    del create_missing
    return ensure_agent_docs(repo_root, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure repository knowledge references in AGENTS.md and CLAUDE.md.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--output", help="Knowledge output directory")
    parser.add_argument("--create-missing", action="store_true", help="Deprecated; missing files are always created")
    args = parser.parse_args()
    try:
        result = link_agent_docs(args.repo_root, args.output, args.create_missing)
    except (AgentDocumentError, OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
