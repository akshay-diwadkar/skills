#!/usr/bin/env python3
"""Validate the standalone engineering-skill repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "skills" / "engineering"
ALLOWED_TOP_LEVEL = {"SKILL.md", "scripts", "references", "schemas", "templates", "assets", "requirements.txt", ".env.example"}
FORBIDDEN_PARTS = {"agents", "evals", "fixtures", "__pycache__"}
RETIRED_PATHS = (
    "catalog",
    "docs",
    "skills-lock.json",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "VERSION",
    "tools/catalog",
    "tools/packaging",
    "tools/release",
    ".github/CODEOWNERS",
    ".github/ISSUE_TEMPLATE",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/scripts",
    ".github/workflows/release.yml",
    ".github/workflows/repository-contract.yml",
)


def discover_skills() -> list[Path]:
    if not SKILLS_ROOT.is_dir():
        return []
    return sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())


def validate_frontmatter(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.relative_to(ROOT)}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{skill_md.relative_to(ROOT)}: missing YAML frontmatter"]
    frontmatter = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    errors: list[str] = []
    if not name or name.group(1).strip() != skill_dir.name:
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter name must match the skill directory")
    if not description or not description.group(1).strip():
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter description is required")
    return errors


def validate_skill_package(skill_dir: Path) -> list[str]:
    errors = validate_frontmatter(skill_dir)
    for child in skill_dir.iterdir():
        if child.name not in ALLOWED_TOP_LEVEL:
            errors.append(f"{child.relative_to(ROOT)}: unsupported skill-package resource")
    for path in skill_dir.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            errors.append(f"{path.relative_to(ROOT)}: development or platform artifact inside skill package")
    return errors


def validate_script_references(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    text = skill_md.read_text(encoding="utf-8")
    errors: list[str] = []
    for reference in re.findall(r"python\s+[\"']?(scripts[/\\][A-Za-z0-9_-]+\.py)[\"']?", text):
        if not (skill_dir / reference.replace("\\", "/")).is_file():
            errors.append(f"{skill_md.relative_to(ROOT)}: references missing bundled script {reference}")
    return errors


def validate_retired_surfaces() -> list[str]:
    """Reject tracked-style platform surfaces while tolerating ignored bytecode caches."""
    errors: list[str] = []
    for relative_path in RETIRED_PATHS:
        path = ROOT / relative_path
        if path.is_file():
            errors.append(f"Retired platform artifact remains: {relative_path}")
        elif path.is_dir() and any("__pycache__" not in child.parts for child in path.rglob("*")):
            errors.append(f"Retired platform artifact remains: {relative_path}")
    return errors


def main() -> int:
    skills = discover_skills()
    errors = ["No skills found under skills/engineering"] if not skills else []
    for skill_dir in skills:
        errors.extend(validate_skill_package(skill_dir))
        errors.extend(validate_script_references(skill_dir))
    errors.extend(validate_retired_surfaces())
    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in sorted(set(errors)):
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Repository validation passed for {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
