#!/usr/bin/env python3
"""Validate tracked skill metadata and forbidden tracked files."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "skills-lock.json"
FORBIDDEN_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
FORBIDDEN_SKILL_DIR_NAMES = {
    "benchmark",
    "benchmarks",
    "eval",
    "evals",
    "fixture",
    "fixtures",
    "test",
    "testdata",
    "tests",
}
FORBIDDEN_SKILL_FILE_NAMES = {
    "browser_smoke.py",
    "check_template_refs.py",
    "conftest.py",
    "debug_hash.py",
}
TEST_FILE_RE = re.compile(r"(?:^test_.+|.+_test)\.(?:js|jsx|py|sh|ts|tsx)$", re.IGNORECASE)
SCORER_FILE_RE = re.compile(r"^score_.+\.(?:js|py|ts)$", re.IGNORECASE)
EXPECTED_RUNTIME_FILE_COUNTS = {
    "codebase-issue-auditor": 12,
    "create-diagram": 11,
    "design-codebase-with-senior-dev": 8,
    "github-issue-planner": 8,
    "implement-with-senior-dev": 5,
    "optimize-codebase-with-senior-dev": 11,
    "plan-with-senior-dev": 15,
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
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line and (ROOT / line).is_file()]


def has_forbidden_marker(path: str) -> bool:
    parts = set(Path(path).parts)
    return path.endswith("/.env") or bool(parts & FORBIDDEN_PATH_PARTS)


def load_skills_lock() -> tuple[dict[str, Any] | None, list[str]]:
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{LOCK_PATH.relative_to(ROOT)} is invalid: {exc}"]

    if not isinstance(lock, dict):
        return None, ["skills-lock.json must contain a JSON object"]
    return lock, []


def validate_locked_skills(lock: dict[str, Any]) -> list[str]:
    errors: list[str] = []

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


def forbidden_skill_artifact(path: str, skill_names: set[str]) -> bool:
    parts = Path(path).as_posix().split("/")
    if len(parts) < 2 or parts[0] not in skill_names:
        return False

    directories = {part.lower() for part in parts[1:-1]}
    filename = parts[-1].lower()
    return bool(
        directories & FORBIDDEN_SKILL_DIR_NAMES
        or filename in FORBIDDEN_SKILL_FILE_NAMES
        or TEST_FILE_RE.fullmatch(filename)
        or SCORER_FILE_RE.fullmatch(filename)
    )


def validate_tracked_files(tracked_files: list[str]) -> list[str]:
    forbidden = [path for path in tracked_files if has_forbidden_marker(path)]
    return [f"forbidden tracked file: {path}" for path in forbidden]


def validate_skill_distribution(tracked_files: list[str], skill_names: set[str]) -> list[str]:
    forbidden = [path for path in tracked_files if forbidden_skill_artifact(path, skill_names)]
    return [f"development artifact inside distributable skill: {path}" for path in forbidden]


def validate_runtime_file_counts(tracked_files: list[str], expected_counts: dict[str, int]) -> list[str]:
    errors: list[str] = []
    for skill_name, expected in expected_counts.items():
        actual = sum(path.startswith(f"{skill_name}/") for path in tracked_files)
        if actual != expected:
            errors.append(f"{skill_name}: expected {expected} runtime files, found {actual}")
    return errors


def main() -> int:
    lock, errors = load_skills_lock()
    tracked_files = git_tracked_files()
    errors.extend(validate_tracked_files(tracked_files))
    if lock is not None:
        errors.extend(validate_locked_skills(lock))
        skills = lock.get("skills")
        if isinstance(skills, dict):
            skill_names = set(skills)
            errors.extend(validate_skill_distribution(tracked_files, skill_names))
            expected_counts = {
                name: count for name, count in EXPECTED_RUNTIME_FILE_COUNTS.items() if name in skill_names
            }
            errors.extend(validate_runtime_file_counts(tracked_files, expected_counts))
    if errors:
        print("Skill tree validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Skill tree validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
