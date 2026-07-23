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
        return yaml.safe_load(f)


def run_mypy_group(label: str, targets: list[str]) -> bool:
    valid_targets = [t for t in targets if (ROOT / t).exists()]
    if not valid_targets:
        return True

    cmd = [sys.executable, "-m", "mypy"] + valid_targets
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

    skills = catalog.get("skills", [])
    all_passed = True

    for skill in skills:
        name = skill.get("name")
        if not name:
            raise ValueError("Every catalog skill requires a non-empty name")

        skill_path = skill.get("path")
        test_path = skill.get("tests")

        targets = []
        if skill_path:
            targets.append(skill_path)
        if test_path:
            targets.append(test_path)

        if not run_mypy_group(f"skill: {name}", targets):
            all_passed = False

    tooling_targets = [
        "tools",
        "tests/repository",
        "tests/integration",
        ".github/scripts",
    ]

    if not run_mypy_group("repository tooling", tooling_targets):
        all_passed = False

    if not all_passed:
        return 1

    print("All mypy checks passed cleanly across isolated skill and tooling scopes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
