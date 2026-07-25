"""Deterministic source-tree fingerprint engine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash (truncated to 16 hex chars) of a single file."""
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
        return h.hexdigest()[:16]
    except Exception:
        return ""


def compute_source_fingerprint(
    repo_root: Path,
    indexed_files: list[str],
    config: dict[str, Any],
) -> str:
    """Compute a deterministic SHA-256 fingerprint for the indexed source tree.
    
    Excludes .agent/knowledge/** and generated agent doc blocks so commits of generated docs
    do not invalidate freshness.
    """
    root = Path(repo_root).resolve()
    h = hashlib.sha256()

    # Config fingerprint component
    config_bytes = json.dumps(config, sort_keys=True).encode("utf-8")
    h.update(config_bytes)

    # Sort indexed file paths to guarantee deterministic hash calculation
    for rel_str in sorted(indexed_files):
        # Ignore knowledge directory artifacts and managed agent blocks in root files
        if rel_str.startswith(".agent/knowledge"):
            continue

        full_p = root / rel_str
        if full_p.is_file():
            h.update(rel_str.encode("utf-8"))
            h.update(compute_file_hash(full_p).encode("utf-8"))

    return h.hexdigest()[:16]
