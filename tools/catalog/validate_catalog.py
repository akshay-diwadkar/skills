#!/usr/bin/env python3
"""Validate catalog/skills.yaml structure, schema, and filesystem alignment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML (yaml) is required.", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
SCHEMA_PATH = ROOT / "catalog" / "skills.schema.json"


def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(f"Catalog file not found at {CATALOG_PATH}")
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_catalog() -> list[str]:
    errors: list[str] = []
    if not CATALOG_PATH.is_file():
        return [f"Missing catalog file: {CATALOG_PATH.relative_to(ROOT)}"]

    try:
        catalog = load_catalog()
    except Exception as exc:
        return [f"Failed to parse catalog YAML: {exc}"]

    if not isinstance(catalog, dict):
        return ["catalog/skills.yaml must contain a top-level mapping"]

    schema_ver = catalog.get("schema_version")
    if schema_ver != 1:
        errors.append(f"Expected schema_version 1, got {schema_ver}")

    domains = catalog.get("domains", {})
    if not isinstance(domains, dict) or not domains:
        errors.append("Catalog 'domains' must be a non-empty mapping")

    skills = catalog.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append("Catalog 'skills' must be a non-empty list")
        return errors

    seen_names = set()
    seen_paths = set()

    for idx, skill in enumerate(skills):
        prefix = f"skill[{idx}] ({skill.get('name', 'unnamed')})"

        name = skill.get("name")
        if not name:
            errors.append(f"{prefix}: missing name")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate name '{name}'")
        else:
            seen_names.add(name)

        rel_path_str = skill.get("path")
        if not rel_path_str:
            errors.append(f"{prefix}: missing path")
        else:
            if rel_path_str in seen_paths:
                errors.append(f"{prefix}: duplicate path '{rel_path_str}'")
            seen_paths.add(rel_path_str)

            path = ROOT / rel_path_str
            if not path.is_dir():
                errors.append(f"{prefix}: path '{rel_path_str}' does not exist on disk as a directory")
            else:
                skill_md = path / "SKILL.md"
                if not skill_md.is_file():
                    errors.append(f"{prefix}: missing SKILL.md inside '{rel_path_str}'")

        domain = skill.get("domain")
        if not domain or domain not in domains:
            errors.append(f"{prefix}: invalid or undeclared domain '{domain}'")

        status = skill.get("status")
        if status not in ("experimental", "beta", "stable", "deprecated"):
            errors.append(f"{prefix}: invalid status '{status}'")

        kind = skill.get("kind")
        if kind not in ("workflow", "discipline", "utility"):
            errors.append(f"{prefix}: invalid kind '{kind}'")

        invocation = skill.get("invocation")
        if invocation not in ("user", "model", "both"):
            errors.append(f"{prefix}: invalid invocation '{invocation}'")

        doc_path_str = skill.get("documentation")
        if doc_path_str:
            doc_path = ROOT / doc_path_str
            if not doc_path.is_file():
                errors.append(f"{prefix}: documentation path '{doc_path_str}' does not exist on disk")

        test_path_str = skill.get("tests")
        if test_path_str:
            test_path = ROOT / test_path_str
            if not test_path.is_dir():
                errors.append(f"{prefix}: test path '{test_path_str}' does not exist on disk")

    return errors


def main() -> int:
    errors = validate_catalog()
    if errors:
        print("Catalog validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Catalog validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
