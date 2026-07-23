#!/usr/bin/env python3
"""Validate skill relationships and dependency declarations."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required.", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"


def validate_dependencies() -> list[str]:
    errors = []
    if not CATALOG_PATH.is_file():
        return ["Missing catalog/skills.yaml"]

    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    skills = {s["name"]: s for s in catalog.get("skills", [])}

    for name, skill in skills.items():
        rel = skill.get("relationships", {})
        for inv in rel.get("invokes", []):
            if inv not in skills:
                errors.append(f"Skill '{name}' invokes declared unknown skill '{inv}'")
        for comp in rel.get("complements", []):
            if comp not in skills:
                errors.append(f"Skill '{name}' complements declared unknown skill '{comp}'")

    return errors


def main() -> int:
    errors = validate_dependencies()
    if errors:
        print("Dependency validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Dependency validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
