"""Portable v4 repository snapshot, binding, and receipt primitives.

This file is the canonical source; the identical copy in implement-plan is
checked by tests so each installed skill remains independently executable.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

RECEIPT_RE = re.compile(
    r"^<!-- plan-validation: 4; body-sha256: (?P<body>[0-9a-f]{64}); binding-sha256: (?P<binding>[0-9a-f]{64}) -->$"
)
PREFIX = "<!-- plan-validation:"


def canonical_text(text: str) -> str:
    return (
        "\n".join(
            line
            for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
            if not line.lstrip().startswith(PREFIX)
        ).rstrip("\n")
        + "\n"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def plan_digest(text: str) -> str:
    return sha256_bytes(canonical_text(text).encode("utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def binding_digest(binding: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(binding).encode("utf-8"))


def _run(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def repo_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files: list[dict[str, str]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        relative = path.relative_to(root).as_posix()
        files.append({"path": relative, "sha256": sha256_bytes(path.read_bytes())})
    head = _run(root, "rev-parse", "HEAD")
    remote = _run(root, "config", "--get", "remote.origin.url")
    status = _run(root, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "root": str(root),
        "git_head": head or None,
        "repository_id": remote or str(root),
        "dirty": bool(status),
        "status": status.splitlines(),
        "tree": files,
    }


def write_snapshot(root: Path, output: Path) -> dict[str, Any]:
    snapshot = repo_snapshot(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def load_snapshot(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or "tree" not in value:
        raise ValueError("snapshot must be a repository snapshot object")
    return value


def snapshot_matches(root: Path, baseline: dict[str, Any]) -> bool:
    current = repo_snapshot(root)
    return canonical_json(current) == canonical_json(baseline)


def receipt_line(text: str, binding: dict[str, Any]) -> str:
    return f"<!-- plan-validation: 4; body-sha256: {plan_digest(text)}; binding-sha256: {binding_digest(binding)} -->"


def finalized_text(text: str, binding: dict[str, Any]) -> str:
    body = canonical_text(text)
    lines = body.rstrip("\n").splitlines()
    insertion = next((i + 1 for i, line in enumerate(lines) if line.startswith("<!-- plan-repository:")), 1)
    lines.insert(insertion, receipt_line(body, binding))
    return "\n".join(lines) + "\n"
