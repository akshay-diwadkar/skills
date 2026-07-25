"""Deterministic file discovery engine with inclusion, exclusion, and binary filtering."""

from __future__ import annotations

import os
import re
import subprocess
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

    tracked = git_tracked_paths(root)
    if tracked is None:
        candidates = _walk_files(root)
    else:
        untracked = git_untracked_paths(root) if config.get("include_untracked", True) else []
        candidates = sorted(set(tracked) | set(untracked))
    for rel_str in candidates:
        full_path = root / rel_str
        if not full_path.exists() or full_path.is_symlink() or not _safe_path(root, full_path):
            ignored.append(rel_str)
            continue
        if matches_glob(rel_str, excludes) or (includes and not matches_glob(rel_str, includes)):
            ignored.append(rel_str)
            continue
        try:
            if full_path.stat().st_size > max_size or is_binary_file(full_path):
                ignored.append(rel_str)
                continue
        except OSError:
            ignored.append(rel_str)
            continue
        if matches_glob(rel_str, gen_patterns):
            generated.append(rel_str)
        included.append(rel_str)
    return sorted(included), sorted(generated), sorted(set(ignored))


def _safe_path(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def git_tracked_paths(root: Path) -> set[str] | None:
    """Return one deterministic tracked-path inventory, or ``None`` outside Git."""
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=False)
    if result.returncode:
        return None
    return {
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def git_untracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root, capture_output=True, check=False
    )
    if result.returncode:
        return []
    return sorted(item.decode("utf-8", errors="surrogateescape").replace("\\", "/") for item in result.stdout.split(b"\0") if item)


def is_tracked_path(root: Path, path: str, tracked_paths: set[str] | None = None) -> bool:
    """Determine tracking from a shared inventory; non-Git fallback remains permissive."""
    inventory = tracked_paths if tracked_paths is not None else git_tracked_paths(root)
    if inventory is None:
        return True
    return path.replace("\\", "/") in inventory


def _walk_files(root: Path) -> list[str]:
    """Filesystem fallback used only when Git metadata is unavailable."""
    result: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Sort directories for deterministic traversal order
        dirnames.sort()

        dirnames[:] = [name for name in dirnames if not name.startswith(".")]

        # Sort filenames for deterministic file processing
        filenames.sort()

        for fname in filenames:
            full_path = Path(dirpath) / fname
            result.append(str(full_path.relative_to(root)).replace("\\", "/"))
    return sorted(result)
