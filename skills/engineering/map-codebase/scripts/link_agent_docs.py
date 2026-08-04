#!/usr/bin/env python3
"""Maintain managed repository-knowledge references in agent instruction files."""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from knowledge.config import load_config, resolve_knowledge_directory

MANAGED_BEGIN = "<!-- BEGIN MAP-CODEBASE -->"
MANAGED_END = "<!-- END MAP-CODEBASE -->"
LEGACY_MANAGED_BEGIN = "<!-- BEGIN BUILD-CODEBASE-KNOWLEDGE -->"
LEGACY_MANAGED_END = "<!-- END BUILD-CODEBASE-KNOWLEDGE -->"
OPT_OUT = "<!-- OPT-OUT MAP-CODEBASE -->"
KNOWLEDGE_GUIDE = "KNOWLEDGE.md"
REPOSITORY_KNOWLEDGE_HEADING = "## Repository Knowledge"


class AgentDocumentError(ValueError):
    """A supported instruction file has an unsafe managed-block state."""


@dataclass(frozen=True)
class PlannedAgentDoc:
    path: Path
    name: str
    action: Literal["created", "modified", "unchanged", "skipped"]
    original_exists: bool
    original_bytes: bytes | None
    final_bytes: bytes
    mode: int | None


def generate_managed_block(rel_k_path: str) -> str:
    """Generate the concise repository-knowledge instruction section."""
    return (
        f"{REPOSITORY_KNOWLEDGE_HEADING}\n"
        f"Read `{rel_k_path}/{KNOWLEDGE_GUIDE}` before repository exploration.\n"
        "Use the `map-codebase` resolver as the default navigation entry point: "
        "resolve phase 1 for the current task, read only returned targets and selected symbol shards, "
        "and expand only when its stop condition is unmet. Verify conclusions in source."
    )


def generate_knowledge_guide() -> str:
    """Generate static orientation for the repository-knowledge directory."""
    return """# Repository Knowledge

Use this directory for repository navigation; verify selected conclusions in current source.

## Assets

- `manifest.json`: freshness, integrity, and indexed-path inventory.
- `repo-map.json`: files, subsystems, entry points, commands, and configuration.
- `symbol-index.json`: compact symbol lookup; `symbols.json` locates `symbols/*.json` detail shards.
- `relationships.json`: imports, calls, test/configuration/generated links, and reverse imports.
- `evidence-index.json`: locates reusable per-file `evidence/*.json` extraction shards.

## Workflow

1. Check freshness before broad exploration; build or refresh only when missing, invalid, or stale.
2. Use the `map-codebase` resolver at phase 1; read only returned targets and selected symbol shards, then expand only when its stop condition is unmet.
3. Do not preload maps or shards. Knowledge guides navigation; source remains authoritative.
"""


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


def _find_heading_section(content: str, filename: str) -> tuple[int, int] | None:
    """Find the one markerless repository-knowledge section."""
    positions: list[tuple[int, int]] = []
    offset = 0
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.rstrip("\r\n") == REPOSITORY_KNOWLEDGE_HEADING:
            positions.append((index, offset))
        offset += len(line)
    if not positions:
        return None
    if len(positions) != 1:
        raise AgentDocumentError(f"duplicate Repository Knowledge headings in {filename}")
    line_index, start = positions[0]
    end = len(content)
    offset = start + len(lines[line_index])
    for line in lines[line_index + 1 :]:
        if line.startswith("# ") or line.startswith("## "):
            end = offset
            break
        offset += len(line)
    return start, end


def _find_managed_block(content: str, filename: str) -> tuple[int, int] | None:
    """Return one legacy marker block or one markerless owned section."""
    canonical = _find_block(content, filename, MANAGED_BEGIN, MANAGED_END, "MAP-CODEBASE")
    legacy = _find_block(content, filename, LEGACY_MANAGED_BEGIN, LEGACY_MANAGED_END, "legacy MAP-CODEBASE")
    if canonical is not None and legacy is not None:
        raise AgentDocumentError(f"ambiguous MAP-CODEBASE blocks in {filename}")
    marker_block = canonical or legacy
    heading_block = _find_heading_section(content, filename)
    if marker_block is not None:
        if heading_block is not None and not (marker_block[0] <= heading_block[0] < marker_block[1]):
            raise AgentDocumentError(f"ambiguous MAP-CODEBASE blocks in {filename}")
        return marker_block
    return heading_block


def _newline_style(content: str) -> str:
    return "\r\n" if "\r\n" in content else "\n"


def _append_block(content: str, block: str, newline: str) -> str:
    if not content:
        return block
    separator = newline if content.endswith(("\n", "\r")) else newline * 2
    return f"{content}{separator}{block}"


def _planned_content(
    path: Path,
    title: str,
    managed_block: str,
    original_exists: bool,
    original_bytes: bytes | None,
) -> tuple[str, str]:
    """Return the action and complete replacement text without writing the file."""
    if not original_exists:
        return "created", f"# {title}\n\n{managed_block}"

    assert original_bytes is not None
    content = original_bytes.decode("utf-8")
    if OPT_OUT in content:
        return "skipped", content

    newline = _newline_style(content)
    block = managed_block.replace("\n", newline)
    located = _find_managed_block(content, path.name)
    if located is None:
        final = _append_block(content, block, newline)
    else:
        start, end = located
        suffix = content[end:]
        separator = newline * 2 if suffix.startswith(("# ", "## ")) else ""
        final = f"{content[:start]}{block}{separator}{suffix}"
    return ("unchanged" if final == content else "modified"), final


def _plan_agent_doc(path: Path, title: str, managed_block: str) -> PlannedAgentDoc:
    original_exists = path.exists()
    if original_exists and not path.is_file():
        raise AgentDocumentError(f"instruction path is not a file: {path.name}")
    original_bytes = path.read_bytes() if original_exists else None
    mode = stat.S_IMODE(path.stat().st_mode) if original_exists else None
    action, content = _planned_content(path, title, managed_block, original_exists, original_bytes)
    return PlannedAgentDoc(
        path=path,
        name=title,
        action=cast(Literal["created", "modified", "unchanged", "skipped"], action),
        original_exists=original_exists,
        original_bytes=original_bytes,
        final_bytes=content.encode("utf-8"),
        mode=mode,
    )


def _plan_knowledge_guide(knowledge_dir: Path) -> PlannedAgentDoc:
    """Plan replacement of the static, skill-owned knowledge guide."""
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    path = knowledge_dir / KNOWLEDGE_GUIDE
    original_exists = path.exists()
    if original_exists and not path.is_file():
        raise AgentDocumentError(f"knowledge guide path is not a file: {path.name}")
    original_bytes = path.read_bytes() if original_exists else None
    mode = stat.S_IMODE(path.stat().st_mode) if original_exists else None
    final_bytes = generate_knowledge_guide().encode("utf-8")
    action = "created" if not original_exists else ("unchanged" if original_bytes == final_bytes else "modified")
    return PlannedAgentDoc(path, KNOWLEDGE_GUIDE, cast(Literal["created", "modified", "unchanged", "skipped"], action), original_exists, original_bytes, final_bytes, mode)


def _atomic_replace(path: Path, content: bytes, mode: int | None = None) -> None:
    """Replace one target from a same-directory temporary file."""
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.map-codebase-", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _rollback(planned: list[PlannedAgentDoc]) -> list[str]:
    failures: list[str] = []
    for item in reversed(planned):
        try:
            if item.original_exists:
                assert item.original_bytes is not None
                _atomic_replace(item.path, item.original_bytes, item.mode)
            elif item.path.exists():
                item.path.unlink()
        except Exception as exc:  # rollback must report every restoration failure
            failures.append(f"{item.name}: {exc}")
    return failures


def ensure_knowledge_guide(knowledge_dir: Path | str) -> str:
    """Ensure static orientation exists without making it a freshness artifact."""
    planned = _plan_knowledge_guide(Path(knowledge_dir))
    if planned.action in {"created", "modified"}:
        _atomic_replace(planned.path, planned.final_bytes, planned.mode)
    return planned.action


def ensure_agent_docs(repo_root: Path | str, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Ensure the guide and both supported instruction files are current."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    knowledge_dir = resolve_knowledge_directory(root, output_dir, config)
    rel_k_path = knowledge_dir.relative_to(root).as_posix()
    block = generate_managed_block(rel_k_path)
    targets = ((root / "AGENTS.md", "AGENTS.md"), (root / "CLAUDE.md", "CLAUDE.md"))

    # Plan and validate every target before changing any of them.
    guide = _plan_knowledge_guide(knowledge_dir)
    planned = [guide, *[_plan_agent_doc(path, name, block) for path, name in targets]]
    result: dict[str, Any] = {
        "status": "success",
        "created": [],
        "modified": [],
        "unchanged": [],
        "skipped": [],
        "knowledge_path": rel_k_path,
        "knowledge_guide": guide.action,
    }
    changed: list[PlannedAgentDoc] = []
    try:
        for item in planned:
            if item.action in {"created", "modified"}:
                # Include the item before the write: an injected or platform error may
                # occur after a successful replacement but before it returns.
                changed.append(item)
                _atomic_replace(item.path, item.final_bytes, item.mode)
    except Exception as exc:
        rollback_failures = _rollback(changed)
        message = f"failed to commit agent documents: {exc}"
        if rollback_failures:
            message += f"; rollback incomplete: {'; '.join(rollback_failures)}"
        raise AgentDocumentError(message) from exc
    for item in planned[1:]:
        result[item.action].append(item.name)
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
