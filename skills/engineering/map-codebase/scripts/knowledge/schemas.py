"""Schema and cross-artifact validation for v2 knowledge."""

from __future__ import annotations

import json
from functools import lru_cache
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


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Any:
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema)


def validate_schema_json(data: dict[str, Any], schema_name: str) -> list[str]:
    try:
        error = next(_validator(schema_name).iter_errors(data), None)
        if error is not None:
            return [f"{schema_name}: {error}"]
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
    for edge in relationships.get("generated_links", []):
        if edge["source"] not in paths or edge["target"] not in paths:
            errors.append("Invalid generated-source relationship")
    for edge in relationships.get("calls", []):
        if edge["source"] not in paths or edge["target"] not in paths:
            errors.append("Invalid call relationship")
    for target, sources in relationships.get("reverse_imports", {}).items():
        if target not in paths or any(source not in paths for source in sources):
            errors.append("Invalid reverse import relationship")
    return errors
