"""Deterministic file discovery engine with inclusion, exclusion, and binary filtering."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"(?i)(api_key|secret|password|private_key|auth_token|bearer)\s*=\s*['\"]?[a-zA-Z0-9_\-\.]{8,}"),
    re.compile(r"-----BEGIN (PRIVATE KEY|RSA PRIVATE KEY)-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
]


def matches_glob(rel_path_str: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any glob pattern in patterns."""
    norm_path = rel_path_str.replace("\\", "/").strip("/")
    parts = norm_path.split("/")
    for pat in patterns:
        pat_norm = pat.replace("\\", "/").strip("/")
        segments = [p.strip("/") for p in pat_norm.split("/") if p and p != "**"]
        if len(segments) == 1 and segments[0] in parts:
            return True
        regex = (
            "^"
            + pat_norm.replace(".", r"\.")
            .replace("**/", r"(?:.*/)?")
            .replace("/**", r"(?:/.*)?")
            .replace("*", r"[^/]*")
            .replace("?", r".")
            + "$"
        )
        if re.match(regex, norm_path):
            return True
    return False


def is_binary_file(path: Path) -> bool:
    """Check if a file is binary by inspecting initial bytes."""
    try:
        with path.open("rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
            return False
    except Exception:
        return True


def is_secret_file_or_content(path: Path, content: str) -> bool:
    """Check if a file contains secret credentials or private keys."""
    fname = path.name.lower()
    if fname.startswith(".env") and not fname.endswith(".example"):
        return True
    if any(k in fname for k in ["id_rsa", "credentials", "secret_key", "private_key"]):
        return True
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            return True
    return False


def discover_files(repo_root: Path, config: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Discover files under repo_root.
    
    Returns:
        (included_files, generated_files, ignored_files)
    """
    root = repo_root.resolve()
    included: list[str] = []
    generated: list[str] = []
    ignored: list[str] = []

    includes = config.get("include", [])
    excludes = config.get("exclude", [])
    gen_patterns = config.get("generated", [])
    max_size = config.get("max_file_size_bytes", 1048576)

    for dirpath, dirnames, filenames in os.walk(root):
        # Sort directories for deterministic traversal order
        dirnames.sort()

        rel_dir = Path(dirpath).relative_to(root)
        rel_dir_str = str(rel_dir).replace("\\", "/")

        # Prune hidden or excluded directories
        dirs_to_remove = []
        for d in dirnames:
            sub_rel = f"{rel_dir_str}/{d}".strip("./")
            if d.startswith(".") or matches_glob(sub_rel, excludes):
                dirs_to_remove.append(d)
        for d in dirs_to_remove:
            dirnames.remove(d)

        # Sort filenames for deterministic file processing
        filenames.sort()

        for fname in filenames:
            full_path = Path(dirpath) / fname
            if full_path.is_symlink():
                ignored.append(str(full_path.relative_to(root)).replace("\\", "/"))
                continue

            rel_path = full_path.relative_to(root)
            rel_str = str(rel_path).replace("\\", "/")

            if matches_glob(rel_str, excludes):
                ignored.append(rel_str)
                continue

            if includes and not matches_glob(rel_str, includes) and rel_str not in ["AGENTS.md", "CLAUDE.md", "README.md", "pyproject.toml", "package.json"]:
                ignored.append(rel_str)
                continue

            try:
                if full_path.stat().st_size > max_size:
                    ignored.append(rel_str)
                    continue
            except Exception:
                ignored.append(rel_str)
                continue

            if is_binary_file(full_path):
                ignored.append(rel_str)
                continue

            if matches_glob(rel_str, gen_patterns):
                generated.append(rel_str)

            included.append(rel_str)

    return sorted(included), sorted(generated), sorted(ignored)
