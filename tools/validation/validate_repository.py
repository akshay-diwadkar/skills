#!/usr/bin/env python3
"""Consolidated repository-wide validation tool."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema

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


def validate_skill_references(skills_catalog: dict[str, Any], agents_catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    known_skills = {s["name"] for s in skills_catalog.get("skills", [])}

    for agent in agents_catalog.get("agents", []):
        for sk in agent.get("skills", []):
            if sk not in known_skills:
                errors.append(f"Agent '{agent.get('name')}' in catalog/agents.yaml references unknown skill '{sk}'")

    dollar_pattern = re.compile(r"\$([a-z0-9]+(?:-[a-z0-9]+)+)")
    files_to_check: list[Path] = []
    skills_dir = ROOT / "skills"
    if skills_dir.is_dir():
        files_to_check.extend(skills_dir.rglob("SKILL.md"))
    agents_source_dir = ROOT / "agents" / "source"
    if agents_source_dir.is_dir():
        files_to_check.extend(agents_source_dir.glob("*.md"))

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


SCHEMAS_DIR = ROOT / "tools" / "validation" / "schemas"


def validate_platform_manifest_schemas(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    targets = [
        (ROOT / ".claude-plugin" / "plugin.json", SCHEMAS_DIR / "claude_plugin_schema.json", "Claude plugin"),
        (ROOT / ".claude-plugin" / "marketplace.json", SCHEMAS_DIR / "claude_marketplace_schema.json", "Claude marketplace"),
        (ROOT / ".cursor-plugin" / "plugin.json", SCHEMAS_DIR / "cursor_plugin_schema.json", "Cursor plugin"),
        (ROOT / ".cursor-plugin" / "marketplace.json", SCHEMAS_DIR / "cursor_marketplace_schema.json", "Cursor marketplace"),
    ]

    for manifest_path, schema_path, name in targets:
        if not manifest_path.is_file():
            errors.append(f"Missing manifest: {manifest_path.relative_to(ROOT)}")
            continue
        if not schema_path.is_file():
            errors.append(f"Missing schema: {schema_path.relative_to(ROOT)}")
            continue

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=manifest_data, schema=schema_data)
        except Exception as exc:
            errors.append(f"{name} manifest failed JSON schema validation: {exc}")

    # Discovery & component path validation
    expected_claude_skills = {
        f"./{s['path']}"
        for s in catalog.get("skills", [])
        if s.get("status") in ("stable", "beta") and s.get("platforms", {}).get("claude_plugin", True)
    }
    expected_cursor_skills = {
        f"./{s['path']}"
        for s in catalog.get("skills", [])
        if s.get("status") in ("stable", "beta") and s.get("platforms", {}).get("cursor_plugin", True)
    }

    claude_json = ROOT / ".claude-plugin" / "plugin.json"
    if claude_json.is_file():
        c_data = json.loads(claude_json.read_text(encoding="utf-8"))
        actual_claude = set(c_data.get("skills", []))
        missing = expected_claude_skills - actual_claude
        if missing:
            errors.append(f"Claude plugin manifest missing skills: {sorted(missing)}")

    cursor_json = ROOT / ".cursor-plugin" / "plugin.json"
    if cursor_json.is_file():
        cur_data = json.loads(cursor_json.read_text(encoding="utf-8"))
        actual_cursor = set(cur_data.get("skills", []))
        missing = expected_cursor_skills - actual_cursor
        if missing:
            errors.append(f"Cursor plugin manifest missing skills: {sorted(missing)}")

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

    if not AGENTS_CATALOG_PATH.is_file():
        print("Missing catalog/agents.yaml", file=sys.stderr)
        return 1

    with AGENTS_CATALOG_PATH.open("r", encoding="utf-8") as f:
        agents_catalog = yaml.safe_load(f)

    tracked_files = git_tracked_files()

    errors = []
    errors.extend(validate_skill_discovery(catalog))
    errors.extend(validate_agent_discovery(agents_catalog))
    errors.extend(validate_skill_references(catalog, agents_catalog))
    errors.extend(validate_package_boundaries(tracked_files, catalog))
    errors.extend(validate_skills_lock())
    errors.extend(validate_platform_manifest_schemas(catalog))
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
