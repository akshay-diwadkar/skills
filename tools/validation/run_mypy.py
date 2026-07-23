#!/usr/bin/env python3
"""Run mypy in isolated skill scopes to avoid standalone-module collisions."""

from __future__ import annotations

import subprocess
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


def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(f"Catalog file not found at {CATALOG_PATH}")
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Catalog file must contain a top-level mapping/dictionary")
    return data


def has_python_files(p: Path) -> bool:
    if not p.exists():
        return False
    if p.is_file():
        return p.suffix in (".py", ".pyi")
    if p.is_dir():
        return any(p.rglob("*.py")) or any(p.rglob("*.pyi"))
    return False


def run_mypy_group(label: str, targets: list[str]) -> bool:
    valid_targets: list[str] = []
    for t in targets:
        p = ROOT / t
        if not p.exists():
            print(f"Skipping non-existent target path for {label}: {t}")
        elif not has_python_files(p):
            print(f"Skipping target path with no Python files for {label}: {t}")
        else:
            valid_targets.append(t)

    if not valid_targets:
        print(f"No existing target paths with Python files to check for group: {label}")
        return True

    cmd = [sys.executable, "-m", "mypy", "--no-incremental"] + valid_targets
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"Mypy check failed for group: {label}", file=sys.stderr)
        return False
    return True


def main() -> int:
    try:
        catalog = load_catalog()
    except Exception as exc:
        print(f"Failed to load catalog: {exc}", file=sys.stderr)
        return 1

    if not isinstance(catalog, dict):
        print("Error: Catalog file must contain a top-level mapping/dictionary.", file=sys.stderr)
        return 1

    skills = catalog.get("skills")
    if skills is None or not isinstance(skills, list):
        print("Error: Catalog does not contain a valid 'skills' list.", file=sys.stderr)
        return 1

    failed_scopes: list[str] = []

    for skill in skills:
        if not isinstance(skill, dict):
            print("Error: Malformed catalog skill entry (not a dictionary).", file=sys.stderr)
            failed_scopes.append("malformed-catalog-entry")
            continue

        name = skill.get("name")
        skill_path = skill.get("path")
        test_path = skill.get("tests")

        if not name or not isinstance(name, str):
            print("Error: Catalog skill entry missing or invalid 'name'.", file=sys.stderr)
            failed_scopes.append("malformed-skill-name")
            continue

        if not skill_path or not test_path:
            print(f"Error: Skill '{name}' missing 'path' or 'tests'.", file=sys.stderr)
            failed_scopes.append(f"skill: {name}")
            continue

        label = f"skill: {name}"
        targets = [str(skill_path), str(test_path)]

        if not run_mypy_group(label, targets):
            failed_scopes.append(label)

    tooling_targets = [
        "tools",
        "tests/repository",
        "tests/integration",
        ".github/scripts",
    ]

    tooling_label = "repository tooling"
    if not run_mypy_group(tooling_label, tooling_targets):
        failed_scopes.append(tooling_label)

    if failed_scopes:
        print("\nMypy check summary: Failed scopes:", file=sys.stderr)
        for scope in failed_scopes:
            print(f"  - {scope}", file=sys.stderr)
        return 1

    print("All mypy checks passed cleanly across isolated skill and tooling scopes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
