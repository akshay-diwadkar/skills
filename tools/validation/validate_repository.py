#!/usr/bin/env python3
"""Consolidated repository-wide validation tool."""

from __future__ import annotations

import json
import re
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
SKILLS_CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
LOCK_PATH = ROOT / "skills-lock.json"
VERSION_PATH = ROOT / "VERSION"

sys.path.insert(0, str(ROOT / "tools" / "catalog"))
import sync_catalog  # noqa: E402

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

            try:
                fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
                if fm.get("name") != name:
                    errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter name '{fm.get('name')}' != folder name '{name}'")
                if not fm.get("description", "").strip():
                    errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter description is required")
            except ValueError as exc:
                errors.append(f"{skill_md.relative_to(ROOT)}: {exc}")

    catalog_skills = {s["name"]: s for s in catalog.get("skills", [])}

    for name, skill_path in discovered_skills.items():
        if name not in catalog_skills:
            errors.append(f"Discovered skill '{name}' at {skill_path.relative_to(ROOT)} is missing from catalog/skills.yaml")

    for name, cat_entry in catalog_skills.items():
        cat_path = ROOT / cat_entry["path"]
        if not cat_path.is_dir():
            errors.append(f"Catalog skill '{name}' path '{cat_entry['path']}' does not exist on disk")

    return errors



def parse_yaml_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter marker")
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    else:
        raise ValueError("missing closing frontmatter marker")
    return yaml.safe_load("\n".join(fm_lines)) or {}


ALLOWED_SKILL_SUBDIRS = {"scripts", "references", "assets", "templates", "agents", "schemas"}
ALLOWED_SKILL_EXTENSIONS = {".py", ".md", ".json", ".html", ".css", ".js", ".yaml", ".yml", ".png", ".jpg", ".svg", ".txt", ".example"}
ALLOWED_SKILL_ROOT_FILES = {"SKILL.md", ".env.example"}
ALLOWED_SKILL_SCRIPTS: dict[str, set[str]] = {
    "build-codebase-knowledge": {
        "__init__.py",
        "benchmarking",
        "benchmark_knowledge.py",
        "build_knowledge.py",
        "cli.py",
        "knowledge",
        "link_agent_docs.py",
        "refresh_knowledge.py",
        "resolve_task.py",
        "resolver",
        "scaffold_github_workflow.py",
        "validate_knowledge.py",
    },
    "codebase-issue-auditor": {
        "audit_bundle.py",
        "check_github_env.py",
        "publish_github_issues.py",
        "validate_audit_bundle.py",
    },
    "create-diagram": {
        "_diagram_utils.py",
        "build_diagram.py",
        "validate_diagram.py",
    },
    "design-codebase-with-senior-dev": {
        "assessment_contract.py",
        "check_assessment.py",
        "finalize_assessment.py",
        "scaffold_assessment.py",
    },
    "github-issue-planner": {
        "check_github_env.py",
        "check_issue_plan.py",
        "fetch_github_issues.py",
        "github_common.py",
        "post_merge_issue_followup.py",
        "scaffold_issue_plan.py",
    },
    "implement-with-senior-dev": {
        "_plan_utils.py",
        "check_implementation.py",
        "finalize_implementation.py",
        "implementation_contract.py",
        "scaffold_implementation.py",
    },
    "optimize-codebase-with-senior-dev": {
        "check_optimization.py",
        "optimization_contract.py",
        "scaffold_optimization.py",
    },
    "plan-with-senior-dev": {
        "_plan_utils.py",
        "check_plan.py",
        "check_plan_rubric.py",
        "check_plan_shape.py",
        "finalize_plan.py",
        "plan_contract.py",
        "plan_model.py",
        "scaffold_plan.py",
    },
}


def validate_package_boundaries(tracked_files: list[str], catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    catalog_skills = {s["name"]: s["path"] for s in catalog.get("skills", [])}

    for path in tracked_files:
        parts = Path(path).parts
        if any(part in FORBIDDEN_DIR_NAMES for part in parts) or (path.endswith(".env") and not path.endswith(".env.example")):
            errors.append(f"Forbidden tracked file: {path}")

        if len(parts) >= 3 and parts[0] == "skills":
            skill_name = parts[2]
            filename = parts[-1].lower()
            dirs = {p.lower() for p in parts[3:-1]}

            if dirs & FORBIDDEN_SKILL_DIR_NAMES or filename in FORBIDDEN_SKILL_FILE_NAMES or filename.startswith("test_") or filename.endswith("_test.py"):
                errors.append(f"Development artifact inside distributable skill: {path}")
                continue

            rel_parts = parts[3:]
            if len(rel_parts) == 1:
                if rel_parts[0] not in ALLOWED_SKILL_ROOT_FILES:
                    ext = Path(rel_parts[0]).suffix.lower()
                    if ext not in ALLOWED_SKILL_EXTENSIONS:
                        errors.append(f"Unrecognized root runtime file inside skill package '{skill_name}': {path}")
            elif len(rel_parts) > 1:
                top_dir = rel_parts[0].lower()
                if top_dir not in ALLOWED_SKILL_SUBDIRS:
                    errors.append(f"Unrecognized runtime directory inside skill package '{skill_name}': {path}")
                if top_dir == "scripts":
                    allowed_scripts = ALLOWED_SKILL_SCRIPTS.get(skill_name, set())
                    if rel_parts[1] not in allowed_scripts:
                        errors.append(f"Unrecognized runtime script inside skill package '{skill_name}': {path}")
                ext = Path(rel_parts[-1]).suffix.lower()
                if ext not in ALLOWED_SKILL_EXTENSIONS:
                    errors.append(f"Unrecognized runtime file extension inside skill package '{skill_name}': {path}")

    # Ensure every catalog skill has runtime files
    for skill_name, rel_prefix in catalog_skills.items():
        actual = sum(path.startswith(f"{rel_prefix}/") for path in tracked_files)
        if actual == 0:
            errors.append(f"{skill_name}: no runtime files found under {rel_prefix}")

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


def validate_skill_references(skills_catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    known_skills = {s["name"] for s in skills_catalog.get("skills", [])}

    dollar_pattern = re.compile(r"\$([a-z0-9]+(?:-[a-z0-9]+)+)")
    files_to_check: list[Path] = []
    skills_dir = ROOT / "skills"
    if skills_dir.is_dir():
        files_to_check.extend(skills_dir.rglob("SKILL.md"))

    for filepath in files_to_check:
        text = filepath.read_text(encoding="utf-8")
        rel_path = filepath.relative_to(ROOT)
        for match in dollar_pattern.finditer(text):
            ref = match.group(1)
            if ref not in known_skills and ref not in ("skillDir", "repo-root", "issue-json", "senior-plan"):
                errors.append(f"{rel_path}: references unknown skill '${ref}'")

        for line_num, line in enumerate(text.splitlines(), start=1):
            if "Use `" in line or "Invoke `" in line:
                for match in re.finditer(r"`([a-z0-9-]+)`", line):
                    ref = match.group(1)
                    if ("-with-" in ref or "-planner" in ref or "-auditor" in ref or ref in ("diagnose", "improve-codebase-architecture")) and ref not in known_skills:
                        errors.append(f"{rel_path}:{line_num}: references unknown skill '{ref}'")

    return errors


FILESYSTEM_FLAGS = {
    "--repo-root",
    "--plan",
    "--output",
    "--input",
    "--data",
    "--env",
    "--issue-json",
    "--senior-plan",
    "--verification-summary-file",
    "--file",
    "--draft",
    "--report",
    "--changed-file",
    "--tasks",
}


def is_visibly_absolute(path_str: str) -> bool:
    s = path_str.strip("'\"").lower()
    return (
        s.startswith(("/", "\\", "<absolute", "/absolute", "\\absolute"))
        or bool(re.match(r"^[a-z]:[/\\]", s))
        or "/absolute/" in s
        or "\\absolute\\" in s
    )


def validate_command_path_contracts() -> list[str]:
    errors: list[str] = []
    skills_dir = ROOT / "skills" / "engineering"
    if not skills_dir.is_dir():
        return errors

    for skill_folder in skills_dir.iterdir():
        if not skill_folder.is_dir():
            continue
        for md_file in skill_folder.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            rel_path = md_file.relative_to(ROOT)

            code_blocks = re.findall(r"```(?:bash|powershell|sh)?\n(.*?)\n```", content, re.DOTALL)
            for block in code_blocks:
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                normalized_cmds = []
                curr = []
                for line in lines:
                    if line.endswith("\\"):
                        curr.append(line[:-1].strip())
                    else:
                        curr.append(line)
                        normalized_cmds.append(" ".join(curr))
                        curr = []
                if curr:
                    normalized_cmds.append(" ".join(curr))

                for cmd in normalized_cmds:
                    if "python scripts/" not in cmd and "python scripts\\" not in cmd:
                        continue

                    tokens = cmd.split()
                    for i, tok in enumerate(tokens):
                        if tok in FILESYSTEM_FLAGS:
                            if i + 1 < len(tokens):
                                val = tokens[i + 1]
                                if not is_visibly_absolute(val):
                                    errors.append(
                                        f"{rel_path}: option '{tok}' has non-absolute path example '{val}' in command: {cmd}"
                                    )
                        elif i > 0 and tokens[i - 1] not in FILESYSTEM_FLAGS and not tok.startswith("-"):
                            if (
                                tok.startswith(("<run-dir>", "<issue-plan", "<fresh-issue", "<validated-v3-plan", "<summary"))
                                or (any(tok.endswith(ext) for ext in (".md", ".json", ".html", ".py")) and not tok.startswith("scripts/"))
                            ):
                                if i > 1 and tokens[i - 1] in ("--tier", "--task-type", "--level", "--scope", "--stage", "--base", "--github-repo-url", "--issue-number", "--pr-number"):
                                    continue
                                if not is_visibly_absolute(tok):
                                    errors.append(
                                        f"{rel_path}: positional argument has non-absolute path example '{tok}' in command: {cmd}"
                                    )
    return errors


def validate_sync_state() -> list[str]:
    diffs = sync_catalog.sync_all(write=False)
    return [f"Generated surface out of sync: {d}" for d in diffs]


def main() -> int:
    if not SKILLS_CATALOG_PATH.is_file():
        print("Missing catalog/skills.yaml", file=sys.stderr)
        return 1

    with SKILLS_CATALOG_PATH.open("r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    tracked_files = git_tracked_files()

    errors = []
    errors.extend(validate_skill_discovery(catalog))
    errors.extend(validate_skill_references(catalog))
    errors.extend(validate_package_boundaries(tracked_files, catalog))
    errors.extend(validate_skills_lock())
    errors.extend(validate_command_path_contracts())
    errors.extend(validate_sync_state())

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
