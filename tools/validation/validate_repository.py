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
SKILLS_CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
AGENTS_CATALOG_PATH = ROOT / "catalog" / "agents.yaml"
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


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


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


def validate_agent_discovery(agents_catalog: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if agents_catalog is None:
        if not AGENTS_CATALOG_PATH.is_file():
            return ["Missing catalog/agents.yaml"]
        with AGENTS_CATALOG_PATH.open("r", encoding="utf-8") as f:
            agents_catalog = yaml.safe_load(f)

    for agent in agents_catalog.get("agents", []):
        name = agent["name"]

        # Capabilities validation
        capabilities = agent.get("capabilities")
        if not isinstance(capabilities, dict) or "web_research" not in capabilities or not isinstance(capabilities.get("web_research"), bool):
            errors.append(f"Agent '{name}' in catalog/agents.yaml must define boolean 'capabilities.web_research'")
            continue

        web_research = capabilities["web_research"]

        source_path = ROOT / agent["source"]
        if not source_path.is_file():
            errors.append(f"Agent '{name}' source prompt missing: {agent['source']}")
        doc_path = ROOT / agent["documentation"]
        if not doc_path.is_file():
            errors.append(f"Agent '{name}' documentation missing: {agent['documentation']}")

        # Validate adapter permissions and frontmatter
        claude_adapter = ROOT / "agents" / "claude" / f"{name}.md"
        cursor_adapter = ROOT / "agents" / "cursor" / f"{name}.md"
        codex_adapter = ROOT / ".codex" / "agents" / f"{name}.toml"

        if not claude_adapter.is_file():
            errors.append(f"Missing Claude adapter for '{name}'")
        else:
            claude_text = claude_adapter.read_text(encoding="utf-8")
            if "## External Research Policy" not in claude_text:
                errors.append(f"Claude adapter for '{name}' missing External Research Policy")
            try:
                fm = parse_yaml_frontmatter(claude_text)
                tools = fm.get("tools", [])
                if web_research:
                    if tools.count("WebSearch") != 1:
                        errors.append(f"Claude adapter for '{name}' must contain 'WebSearch' tool exactly once")
                    if tools.count("WebFetch") != 1:
                        errors.append(f"Claude adapter for '{name}' must contain 'WebFetch' tool exactly once")
                    if "WebSearch" in tools and "WebFetch" in tools:
                        if tools.index("WebSearch") > tools.index("WebFetch"):
                            errors.append(f"Claude adapter for '{name}' must list 'WebSearch' before 'WebFetch'")
                else:
                    if "WebSearch" in tools:
                        errors.append(f"Claude adapter for '{name}' must omit 'WebSearch' when web_research is false")
                    if "WebFetch" in tools:
                        errors.append(f"Claude adapter for '{name}' must omit 'WebFetch' when web_research is false")
            except Exception as exc:
                errors.append(f"Claude adapter for '{name}' invalid YAML frontmatter: {exc}")

        if not cursor_adapter.is_file():
            errors.append(f"Missing Cursor adapter for '{name}'")
        else:
            cursor_text = cursor_adapter.read_text(encoding="utf-8")
            if "## External Research Policy" not in cursor_text:
                errors.append(f"Cursor adapter for '{name}' missing External Research Policy")
            try:
                fm = parse_yaml_frontmatter(cursor_text)
                if "tools" in fm:
                    errors.append(f"Cursor adapter for '{name}' contains unsupported 'tools' frontmatter key")
            except Exception as exc:
                errors.append(f"Cursor adapter for '{name}' invalid YAML frontmatter: {exc}")

        if not codex_adapter.is_file():
            errors.append(f"Missing Codex adapter for '{name}'")
        else:
            codex_text = codex_adapter.read_text(encoding="utf-8")
            if "## External Research Policy" not in codex_text:
                errors.append(f"Codex adapter for '{name}' missing External Research Policy")
            try:
                data = tomllib.loads(codex_text)
                for invalid_key in ("tools", "web_search", "network_access"):
                    if invalid_key in data:
                        errors.append(f"Codex adapter for '{name}' contains unsupported TOML key '{invalid_key}'")
            except Exception as exc:
                errors.append(f"Codex adapter for '{name}' invalid TOML: {exc}")

    return errors


def validate_package_boundaries(tracked_files: list[str], catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    catalog_skills = {s["name"]: s["path"] for s in catalog.get("skills", [])}

    for path in tracked_files:
        parts = Path(path).parts
        if any(part in FORBIDDEN_DIR_NAMES for part in parts) or path.endswith(".env"):
            errors.append(f"Forbidden tracked file: {path}")

        if len(parts) >= 3 and parts[0] == "skills":
            skill_name = parts[2]
            filename = parts[-1].lower()
            dirs = {p.lower() for p in parts[3:-1]}

            if dirs & FORBIDDEN_SKILL_DIR_NAMES or filename in FORBIDDEN_SKILL_FILE_NAMES:
                errors.append(f"Development artifact inside distributable skill: {path}")

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
    errors.extend(validate_agent_discovery(catalog))
    errors.extend(validate_package_boundaries(tracked_files, catalog))
    errors.extend(validate_skills_lock())
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
