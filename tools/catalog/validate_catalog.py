#!/usr/bin/env python3
"""Validate catalog/skills.yaml and catalog/agents.yaml structure, schema, and filesystem alignment."""

from __future__ import annotations

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


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Catalog file not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_skills_catalog() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not SKILLS_CATALOG_PATH.is_file():
        return {}, [f"Missing catalog file: {SKILLS_CATALOG_PATH.relative_to(ROOT)}"]

    try:
        catalog = load_yaml(SKILLS_CATALOG_PATH)
    except Exception as exc:
        return {}, [f"Failed to parse skills catalog YAML: {exc}"]

    if not isinstance(catalog, dict):
        return {}, ["catalog/skills.yaml must contain a top-level mapping"]

    domains = catalog.get("domains", {})
    skills = catalog.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append("Catalog 'skills' must be a non-empty list")
        return catalog, errors

    seen_names = set()
    seen_paths = set()

    for idx, skill in enumerate(skills):
        prefix = f"skill[{idx}] ({skill.get('name', 'unnamed')})"

        name = skill.get("name")
        if not name:
            errors.append(f"{prefix}: missing name")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate name '{name}'")
        else:
            seen_names.add(name)

        rel_path_str = skill.get("path")
        if not rel_path_str:
            errors.append(f"{prefix}: missing path")
        else:
            if rel_path_str in seen_paths:
                errors.append(f"{prefix}: duplicate path '{rel_path_str}'")
            seen_paths.add(rel_path_str)

            path = ROOT / rel_path_str
            if not path.is_dir():
                errors.append(f"{prefix}: path '{rel_path_str}' does not exist on disk as a directory")
            else:
                skill_md = path / "SKILL.md"
                if not skill_md.is_file():
                    errors.append(f"{prefix}: missing SKILL.md inside '{rel_path_str}'")

        domain = skill.get("domain")
        if not domain or domain not in domains:
            errors.append(f"{prefix}: invalid or undeclared domain '{domain}'")

        status = skill.get("status")
        if status not in ("experimental", "beta", "stable", "deprecated"):
            errors.append(f"{prefix}: invalid status '{status}'")

        kind = skill.get("kind")
        if kind not in ("workflow", "discipline", "utility"):
            errors.append(f"{prefix}: invalid kind '{kind}'")

        invocation = skill.get("invocation")
        if invocation not in ("user", "model", "both"):
            errors.append(f"{prefix}: invalid invocation '{invocation}'")

        doc_path_str = skill.get("documentation")
        if doc_path_str:
            doc_path = ROOT / doc_path_str
            if not doc_path.is_file():
                errors.append(f"{prefix}: documentation path '{doc_path_str}' does not exist on disk")

        test_path_str = skill.get("tests")
        if test_path_str:
            test_path = ROOT / test_path_str
            if not test_path.is_dir():
                errors.append(f"{prefix}: test path '{test_path_str}' does not exist on disk")

    return catalog, errors


def validate_agents_catalog(skills_catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not AGENTS_CATALOG_PATH.is_file():
        return [f"Missing agents catalog file: {AGENTS_CATALOG_PATH.relative_to(ROOT)}"]

    try:
        catalog = load_yaml(AGENTS_CATALOG_PATH)
    except Exception as exc:
        return [f"Failed to parse agents catalog YAML: {exc}"]

    if not isinstance(catalog, dict):
        return ["catalog/agents.yaml must contain a top-level mapping"]

    agents = catalog.get("agents", [])
    if not isinstance(agents, list) or not agents:
        errors.append("Catalog 'agents' must be a non-empty list")
        return errors

    known_skills = {s["name"]: s for s in skills_catalog.get("skills", [])}
    seen_names = set()

    for idx, agent in enumerate(agents):
        prefix = f"agent[{idx}] ({agent.get('name', 'unnamed')})"

        name = agent.get("name")
        if not name:
            errors.append(f"{prefix}: missing name")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate agent name '{name}'")
        else:
            seen_names.add(name)

        status = agent.get("status")
        if status not in ("experimental", "beta", "stable", "deprecated"):
            errors.append(f"{prefix}: invalid status '{status}'")

        source_str = agent.get("source")
        if not source_str:
            errors.append(f"{prefix}: missing source path")
        else:
            source_path = ROOT / source_str
            if not source_path.is_file():
                errors.append(f"{prefix}: source path '{source_str}' does not exist on disk")

        doc_str = agent.get("documentation")
        if not doc_str:
            errors.append(f"{prefix}: missing documentation path")
        else:
            doc_path = ROOT / doc_str
            if not doc_path.is_file():
                errors.append(f"{prefix}: documentation path '{doc_str}' does not exist on disk")

        access = agent.get("access", {})
        if not isinstance(access, dict):
            errors.append(f"{prefix}: 'access' must be a mapping")

        skills = agent.get("skills", [])
        if not isinstance(skills, list):
            errors.append(f"{prefix}: 'skills' must be a list")
        else:
            for skill_name in skills:
                if skill_name not in known_skills:
                    errors.append(f"{prefix}: references unknown skill '{skill_name}'")
                else:
                    skill_entry = known_skills[skill_name]
                    if skill_entry.get("invocation") == "user":
                        errors.append(f"{prefix}: skill '{skill_name}' has invocation mode 'user' which disables model availability")
                    if agent.get("status") == "stable" and skill_entry.get("status") == "deprecated":
                        errors.append(f"{prefix}: stable agent depends on deprecated skill '{skill_name}'")

    return errors


def validate_catalog() -> list[str]:
    skills_catalog, errors = validate_skills_catalog()
    errors.extend(validate_agents_catalog(skills_catalog))
    return errors


def main() -> int:
    errors = validate_catalog()
    if errors:
        print("Catalog validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Catalog validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
