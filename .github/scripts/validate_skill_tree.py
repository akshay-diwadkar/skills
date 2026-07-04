#!/usr/bin/env python3
"""Validate tracked skill metadata and forbidden tracked files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "skills-lock.json"
FORBIDDEN_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter marker")

    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    raise ValueError("missing closing frontmatter marker")


def git_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def has_forbidden_marker(path: str) -> bool:
    parts = set(Path(path).parts)
    return path.endswith("/.env") or bool(parts & FORBIDDEN_PATH_PARTS)


def validate_locked_skills() -> list[str]:
    errors: list[str] = []
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{LOCK_PATH.relative_to(ROOT)} is invalid: {exc}"]

    skills = lock.get("skills")
    if not isinstance(skills, dict) or not skills:
        return ["skills-lock.json must contain a non-empty 'skills' object"]

    for skill_name, raw_meta in skills.items():
        if not isinstance(raw_meta, dict):
            errors.append(f"{skill_name}: lock entry must be an object")
            continue

        raw_skill_path = raw_meta.get("skillPath")
        expected_path = Path(skill_name) / "SKILL.md"
        if raw_skill_path != expected_path.as_posix():
            errors.append(f"{skill_name}: skillPath must be {expected_path.as_posix()}")
            continue

        skill_path = ROOT / expected_path
        if not skill_path.exists():
            errors.append(f"{skill_name}: missing {expected_path.as_posix()}")
            continue

        try:
            frontmatter = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"{expected_path.as_posix()}: {exc}")
            continue

        if frontmatter.get("name") != skill_name:
            errors.append(f"{expected_path.as_posix()}: frontmatter name must be {skill_name!r}")
        if not frontmatter.get("description", "").strip():
            errors.append(f"{expected_path.as_posix()}: frontmatter description is required")

    return errors


def validate_tracked_files() -> list[str]:
    forbidden = [path for path in git_tracked_files() if has_forbidden_marker(path)]
    return [f"forbidden tracked file: {path}" for path in forbidden]


def main() -> int:
    errors = validate_locked_skills() + validate_tracked_files()
    if errors:
        print("Skill tree validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Skill tree validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
