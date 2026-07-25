"""Schema validation and semantic graph consistency engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    jsonschema = None

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


def validate_schema_json(data: dict[str, Any], schema_name: str) -> list[str]:
    """Validate JSON data against JSON schema file in schemas/ directory."""
    errors: list[str] = []
    schema_path = SCHEMAS_DIR / schema_name
    if not schema_path.is_file():
        return [f"Schema file missing: {schema_path}"]

    if jsonschema:
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as exc:
            errors.append(f"JSON schema validation error in {schema_name}: {exc.message}")
        except Exception as exc:
            errors.append(f"Failed to run schema validation: {exc}")
    else:
        # Fallback basic schema shape check
        if "schema_version" not in data:
            errors.append(f"Missing required field 'schema_version' in {schema_name}")

    return errors


def validate_semantic_graph(
    repo_root: Path,
    index_data: dict[str, Any],
    manifest_data: dict[str, Any],
) -> list[str]:
    """Perform deep semantic graph consistency validation."""
    errors: list[str] = []

    files = index_data.get("files", [])
    symbols = index_data.get("symbols", [])
    dependencies = index_data.get("dependencies", [])
    tests = index_data.get("tests", [])
    entry_points = index_data.get("entry_points", [])

    indexed_paths = {f["path"] for f in files}

    # 1. Unique file paths
    if len(indexed_paths) != len(files):
        errors.append("Duplicate file paths detected in index.json")

    # 2. Check line ranges & symbol paths
    for sym in symbols:
        if sym.get("path") not in indexed_paths:
            errors.append(f"Symbol '{sym.get('name')}' references path not in indexed files: '{sym.get('path')}'")
        start = sym.get("line_start", 0)
        end = sym.get("line_end", 0)
        if start > end and end != 0:
            errors.append(f"Invalid line range for symbol '{sym.get('name')}': start={start} > end={end}")

    # 3. Verify dependency endpoints exist or are marked external
    for dep in dependencies:
        src = dep.get("source")
        tgt = dep.get("target")
        if src not in indexed_paths:
            errors.append(f"Dependency source '{src}' does not exist in index")
        if tgt not in indexed_paths:
            errors.append(f"Dependency target '{tgt}' does not exist in index")

    # 4. Verify imported_by agrees with forward imports
    forward_map = {f["path"]: set(f.get("imports", [])) for f in files}
    reverse_map = {f["path"]: set(f.get("imported_by", [])) for f in files}

    for src, imports in forward_map.items():
        for tgt in imports:
            if tgt in reverse_map and src not in reverse_map[tgt]:
                errors.append(f"Reverse import mismatch: '{src}' imports '{tgt}', but '{tgt}' imported_by missing '{src}'")

    # 5. Verify test targets exist
    for t in tests:
        if t.get("path") not in indexed_paths:
            errors.append(f"Test suite '{t.get('path')}' not in indexed files")
        for tgt in t.get("targets", []):
            if tgt not in indexed_paths:
                errors.append(f"Test target '{tgt}' for test '{t.get('path')}' not in indexed files")

    # 6. Verify entry point paths exist
    for ep in entry_points:
        if ep.get("path") not in indexed_paths:
            errors.append(f"Entry point path '{ep.get('path')}' not in indexed files")

    return errors
