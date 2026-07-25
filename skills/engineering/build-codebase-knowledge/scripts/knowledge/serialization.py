"""Deterministic serialization helper functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def serialize_json_deterministic(data: Any, indent: int = 2) -> str:
    """Serialize data into a byte-stable, deterministic JSON string."""
    return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False) + "\n"


def write_file_deterministic(path: Path, content: str) -> None:
    """Write string content with normalized LF newlines to path."""
    normalized = content.replace("\r\n", "\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized, encoding="utf-8")
