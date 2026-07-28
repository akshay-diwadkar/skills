"""Schema and cross-artifact validation for v2 knowledge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:
    requirements = Path(__file__).resolve().parents[2] / "requirements.txt"
    raise RuntimeError(
        f'Missing required dependency "jsonschema"; run '
        f'python -m pip install -r "{requirements}"'
    ) from exc
SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


def validate_schema_json(data: dict[str, Any], schema_name: str) -> list[str]:
    try:
        jsonschema.validate(data, json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8")))
    except Exception as exc:
        return [f"{schema_name}: {exc}"]
    return []


def validate_semantic_graph(
    repo_root: Path,
    repo_map: dict[str, Any],
    relationships: dict[str, Any],
    symbols: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> list[str]:
    paths = {f["path"] for f in repo_map.get("files", [])}
    errors: list[str] = []
    if len(paths) != len(repo_map.get("files", [])):
        errors.append("Duplicate file paths detected")
    symbol_keys = {(symbol.get("path"), symbol.get("name"), symbol.get("line_start")) for symbol in symbols}
    if len(symbol_keys) != len(symbols):
        errors.append("Duplicate symbols detected")
    if paths != set(manifest.get("indexed_paths", [])):
        errors.append("manifest indexed_paths does not match repo map")
    for symbol in symbols:
        if symbol["path"] not in paths or symbol["line_start"] < 1 or symbol["line_end"] < symbol["line_start"]:
            errors.append(f"Invalid symbol: {symbol.get('name')}")
    for edge in relationships.get("imports", []):
        if edge["source"] not in paths or edge["target"] not in paths:
            errors.append("Invalid import relationship")
    for edge in relationships.get("test_links", []):
        if edge["source"] not in paths or edge["target"] not in paths:
            errors.append("Invalid test relationship")
    for target, sources in relationships.get("reverse_imports", {}).items():
        if target not in paths or any(source not in paths for source in sources):
            errors.append("Invalid reverse import relationship")
    return errors
