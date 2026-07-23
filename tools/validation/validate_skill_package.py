#!/usr/bin/env python3
"""Validate an individual skill package for completeness and structure."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def validate_package(skill_path: Path) -> list[str]:
    errors = []
    if not skill_path.is_dir():
        return [f"Skill path {skill_path} is not a directory"]

    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"Missing SKILL.md in {skill_path}")

    # Check for forbidden files inside skill directory
    forbidden_files = ["browser_smoke.py", "conftest.py", "debug_hash.py"]
    for p in skill_path.rglob("*"):
        if p.name.lower() in forbidden_files or "evals" in p.parts or "fixtures" in p.parts:
            errors.append(f"Forbidden development artifact inside skill package: {p.relative_to(ROOT)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a skill package.")
    parser.add_argument("path", type=Path, help="Path to skill package directory")
    args = parser.parse_args()

    errors = validate_package(args.path)
    if errors:
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"Package validation passed for {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
