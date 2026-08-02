"""Shared deterministic primitives for committed realistic benchmark fixtures."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

ASSET_ROOT = Path(__file__).with_name("assets")
GENERATOR_VERSION = "map-codebase-fixtures-v2"


SEMANTIC_DIMENSIONS = (
    ("enterprise", "growth", "startup", "public", "education", "health", "retail", "media", "finance", "industrial"),
    ("atlantic", "pacific", "nordic", "alpine", "coastal", "central", "eastern", "western", "southern", "northern"),
    ("gateway", "console", "scheduler", "stream", "batch", "webhook", "operator", "catalog", "ledger", "archive"),
    ("active", "pending", "settled", "verified", "isolated", "replayed", "migrated", "audited", "bounded", "replicated"),
)


def semantic_slug(index: int) -> str:
    """Encode an ordinal as stable domain vocabulary without numbered clone names."""
    if index < 0 or index >= 10_000:
        raise ValueError("semantic slug index must be between zero and 9999")
    words: list[str] = []
    remaining = index
    for dimension in SEMANTIC_DIMENSIONS:
        words.append(dimension[remaining % len(dimension)])
        remaining //= len(dimension)
    return "_".join(words)


@lru_cache(maxsize=None)
def _ensure_directory(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def write(root: Path, relative: str, content: str) -> None:
    """Write one normalized, contained fixture file."""
    target = (root / relative).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"fixture path escapes root: {relative}")
    _ensure_directory(str(target.parent))
    target.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_bytes(root: Path, relative: str, content: bytes) -> None:
    target = (root / relative).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"fixture path escapes root: {relative}")
    _ensure_directory(str(target.parent))
    target.write_bytes(content)


def asset_text(name: str) -> str:
    return (ASSET_ROOT / name).read_text(encoding="utf-8")


def asset_bytes(name: str) -> bytes:
    return (ASSET_ROOT / name).read_bytes()


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def stable_token(*parts: object) -> str:
    return hashlib.sha256(":".join(map(str, parts)).encode("utf-8")).hexdigest()[:12]


def generated_provenance(*, source: str, input_value: str) -> str:
    """Return deterministic source-of-truth metadata for generated artifacts."""
    digest = hashlib.sha256(input_value.encode("utf-8")).hexdigest()
    return (
        f"// Generated from {source}.\n"
        f"// Generator version: {GENERATOR_VERSION}.\n"
        f"// Input SHA-256: {digest}.\n"
    )


def require_empty_output(output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"fixture output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
