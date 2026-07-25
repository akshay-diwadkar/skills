#!/usr/bin/env python3
"""Shared build/refresh orchestration with agent-document finalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from link_agent_docs import AgentDocumentError, ensure_agent_docs


class KnowledgeFinalizationError(ValueError):
    """Knowledge completed but its required instruction-document step failed."""


def _finalize(result: dict[str, Any], repo_root: Path | str, output_dir: Path | str | None) -> dict[str, Any]:
    try:
        result["agent_docs"] = ensure_agent_docs(repo_root, output_dir)
    except (AgentDocumentError, OSError, UnicodeDecodeError, ValueError) as exc:
        raise KnowledgeFinalizationError(
            f"Knowledge artifacts were created, but agent-document finalization failed: {exc}"
        ) from exc
    return result


def build_and_finalize(
    repo_root: Path | str,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Build knowledge, then finalize both supported agent documents once."""
    from build_knowledge import build_knowledge

    return _finalize(build_knowledge(repo_root, output_dir), repo_root, output_dir)


def refresh_and_finalize(
    repo_root: Path | str,
    changed_files: list[str] | None = None,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Refresh knowledge, then finalize both supported agent documents once."""
    from refresh_knowledge import refresh_knowledge

    return _finalize(refresh_knowledge(repo_root, changed_files, output_dir), repo_root, output_dir)
