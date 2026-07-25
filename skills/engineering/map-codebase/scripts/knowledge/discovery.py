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
GIT_TIMEOUT_SECONDS = 5
UNAVAILABLE_GIT_ROOTS: set[Path] = set()


def run_git(root: Path, *args: str, text: bool = False) -> Any | None:
    """Run a bounded Git command, returning ``None`` when Git is unavailable."""
    resolved_root = root.resolve()
    if resolved_root in UNAVAILABLE_GIT_ROOTS:
        return None
    if not (resolved_root / ".git").exists():
        UNAVAILABLE_GIT_ROOTS.add(resolved_root)
        return None
    try:
        result = subprocess.run(
            ["git", *args], cwd=resolved_root, capture_output=True, text=text, check=False, timeout=GIT_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired):
        UNAVAILABLE_GIT_ROOTS.add(resolved_root)
        return None
    return result if result.returncode == 0 else None


def knowledge_output_prefix(repo_root: Path, output_dir: Path | str) -> str:
    """Return the normalized repository-relative knowledge output prefix."""
    root = repo_root.resolve()
    output = Path(output_dir)
    output = output.resolve() if output.is_absolute() else (root / output).resolve()
    try:
        return output.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("knowledge output must be inside repository") from exc


def is_knowledge_path(repo_root: Path, output_dir: Path | str, path: str) -> bool:
    """Whether ``path`` names the configured internal knowledge output."""
    root = repo_root.resolve()
    candidate = Path(path)
    try:
        relative = (candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()).relative_to(root)
    except ValueError:
        return False
    prefix = knowledge_output_prefix(root, output_dir)
    normalized = relative.as_posix()
    return normalized == prefix or normalized.startswith(prefix + "/")


def is_internal_runtime_path(repo_root: Path, output_dir: Path | str, path: str) -> bool:
    """Whether a path is generated runtime support rather than repository source."""
    normalized = path.replace("\\", "/").strip("/")
    return normalized in {"AGENTS.md", "CLAUDE.md"} or is_knowledge_path(repo_root, output_dir, path)


def filter_internal_paths(repo_root: Path, output_dir: Path | str, paths: list[str] | set[str]) -> list[str]:
    """Return deterministic repository paths excluding generated runtime support."""
    return sorted({path.replace("\\", "/") for path in paths if not is_internal_runtime_path(repo_root, output_dir, path)})


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


def discover_files(
    repo_root: Path, config: dict[str, Any], output_dir: Path | str | None = None
) -> tuple[list[str], list[str], list[str]]:
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
    output = Path(output_dir).resolve() if output_dir is not None else root / config.get("output_dir", ".agent/knowledge")
    for rel_str in filter_internal_paths(root, output, candidates):
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
    result = run_git(root, "ls-files", "-z")
    if result is None:
        return None
    return {
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def git_untracked_paths(root: Path) -> list[str]:
    result = run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if result is None:
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
