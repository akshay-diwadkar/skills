#!/usr/bin/env python3
"""Consolidated repository-wide validation tool."""

from __future__ import annotations

import json
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
LOCK_PATH = ROOT / "skills-lock.json"

FORBIDDEN_DIR_NAMES = {
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

EXPECTED_RUNTIME_FILE_COUNTS = {
    "codebase-issue-auditor": 12,
    "create-diagram": 11,
    "design-codebase-with-senior-dev": 8,
    "github-issue-planner": 11,
    "implement-with-senior-dev": 11,
    "optimize-codebase-with-senior-dev": 12,
    "plan-with-senior-dev": 16,
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
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in result.stdout.splitlines() if line and (ROOT / line).is_file()]
    except Exception:
        # Fallback to filesystem walk if git fails
        files = []
        for p in ROOT.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                files.append(p.relative_to(ROOT).as_posix())
        return files


def validate_skill_discovery(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    discovered_skills: dict[str, Path] = {}

    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        return ["Missing skills/ directory"]

    for domain_dir in skills_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        for skill_dir in domain_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"Expected SKILL.md in {skill_dir.relative_to(ROOT)}")
                continue

            name = skill_dir.name
            if name in discovered_skills:
                errors.append(f"Duplicate skill name '{name}' discovered at {skill_dir.relative_to(ROOT)}")
            else:
                discovered_skills[name] = skill_dir

            # Validate frontmatter
            try:
                fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
                if fm.get("name") != name:
                    errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter name '{fm.get('name')}' != folder name '{name}'")
                if not fm.get("description", "").strip():
                    errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter description is required")
            except ValueError as exc:
                errors.append(f"{skill_md.relative_to(ROOT)}: {exc}")

    catalog_skills = {s["name"]: s for s in catalog.get("skills", [])}

    # Compare discovered vs catalog
    for name, skill_path in discovered_skills.items():
        if name not in catalog_skills:
            errors.append(f"Discovered skill '{name}' at {skill_path.relative_to(ROOT)} is missing from catalog/skills.yaml")

    for name, cat_entry in catalog_skills.items():
        cat_path = ROOT / cat_entry["path"]
        if not cat_path.is_dir():
            errors.append(f"Catalog skill '{name}' path '{cat_entry['path']}' does not exist on disk")

    return errors


def validate_package_boundaries(tracked_files: list[str], catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    catalog_skills = {s["name"]: s["path"] for s in catalog.get("skills", [])}

    for path in tracked_files:
        parts = Path(path).parts
        if any(part in FORBIDDEN_DIR_NAMES for part in parts) or path.endswith(".env"):
            errors.append(f"Forbidden tracked file: {path}")

        # Check if inside a skill directory
        if len(parts) >= 3 and parts[0] == "skills":
            skill_name = parts[2]
            filename = parts[-1].lower()
            dirs = {p.lower() for p in parts[3:-1]}

            if dirs & FORBIDDEN_SKILL_DIR_NAMES or filename in FORBIDDEN_SKILL_FILE_NAMES:
                errors.append(f"Development artifact inside distributable skill: {path}")

    # Check runtime file counts
    for skill_name, expected in EXPECTED_RUNTIME_FILE_COUNTS.items():
        if skill_name in catalog_skills:
            rel_prefix = catalog_skills[skill_name]
            actual = sum(path.startswith(f"{rel_prefix}/") for path in tracked_files)
            if actual != expected:
                errors.append(f"{skill_name}: expected {expected} runtime files under {rel_prefix}, found {actual}")

    return errors


def validate_skills_lock() -> list[str]:
    errors: list[str] = []
    if not LOCK_PATH.is_file():
        return ["Missing skills-lock.json"]

    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"skills-lock.json invalid JSON: {exc}"]

    skills = lock.get("skills", {})
    for skill_name, meta in skills.items():
        expected_path = f"skills/engineering/{skill_name}/SKILL.md"
        actual_path = meta.get("skillPath")
        if actual_path != expected_path:
            errors.append(f"skills-lock.json {skill_name}: skillPath must be '{expected_path}', got '{actual_path}'")

    return errors


def main() -> int:
    if not CATALOG_PATH.is_file():
        print("Missing catalog/skills.yaml", file=sys.stderr)
        return 1

    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    tracked_files = git_tracked_files()

    errors = []
    errors.extend(validate_skill_discovery(catalog))
    errors.extend(validate_package_boundaries(tracked_files, catalog))
    errors.extend(validate_skills_lock())

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
