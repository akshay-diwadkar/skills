#!/usr/bin/env python3
"""Synchronize or check catalog-derived repository surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML (yaml) is required.", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog" / "skills.yaml"
VERSION_PATH = ROOT / "VERSION"
README_PATH = ROOT / "README.md"
ENG_README_PATH = ROOT / "skills" / "engineering" / "README.md"
PLUGIN_JSON_PATH = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON_PATH = ROOT / ".claude-plugin" / "marketplace.json"

BEGIN_MARKER = "<!-- BEGIN GENERATED SKILL CATALOG -->"
END_MARKER = "<!-- END GENERATED SKILL CATALOG -->"


def get_version() -> str:
    if not VERSION_PATH.is_file():
        return "1.0.0"
    return VERSION_PATH.read_text(encoding="utf-8").strip()


def load_catalog() -> dict:
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_root_catalog_markdown(catalog: dict) -> str:
    lines = [
        "| Skill | Domain | Kind | Status | Invocation | Summary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for skill in catalog.get("skills", []):
        name = skill["name"]
        domain = skill["domain"]
        kind = skill["kind"]
        status = skill["status"]
        invocation = skill["invocation"]
        summary = skill["summary"]
        doc = skill.get("documentation", f"docs/skills/{name}.md")
        lines.append(f"| [{name}]({doc}) | `{domain}` | `{kind}` | `{status}` | `{invocation}` | {summary} |")
    return "\n".join(lines)


def render_engineering_readme(catalog: dict) -> str:
    lines = [
        "# Engineering Skills Domain",
        "",
        "This directory contains all canonical engineering skills.",
        "",
    ]

    skills = catalog.get("skills", [])
    kinds = {"workflow": "Workflows", "discipline": "Disciplines", "utility": "Utilities"}

    for k_key, k_title in kinds.items():
        k_skills = [s for s in skills if s.get("kind") == k_key]
        if not k_skills:
            continue
        lines.append(f"## {k_title}")
        lines.append("")
        lines.append("| Skill | Status | Invocation | Summary |")
        lines.append("| --- | --- | --- | --- |")
        for s in k_skills:
            name = s["name"]
            status = s["status"]
            invocation = s["invocation"]
            summary = s["summary"]
            lines.append(f"| [{name}](./{name}/SKILL.md) | `{status}` | `{invocation}` | {summary} |")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_plugin_json(catalog: dict, version: str) -> str:
    promoted_skills = [
        s["path"]
        for s in catalog.get("skills", [])
        if s.get("status") in ("stable", "beta") and s.get("platforms", {}).get("claude_plugin", True)
    ]
    data = {
        "name": "engineering-skills",
        "version": version,
        "description": "Production engineering skills monorepo for software architecture, planning, implementation, auditing, and optimization.",
        "skills": promoted_skills,
    }
    return json.dumps(data, indent=2) + "\n"


def generate_marketplace_json(version: str) -> str:
    data = {
        "name": "engineering-skills-marketplace",
        "plugins": [
            {
                "name": "engineering-skills",
                "version": version,
                "source": "./"
            }
        ]
    }
    return json.dumps(data, indent=2) + "\n"


def update_markdown_section(content: str, generated: str) -> str:
    if BEGIN_MARKER not in content or END_MARKER not in content:
        # Append section if not present
        return content.rstrip() + f"\n\n{BEGIN_MARKER}\n{generated}\n{END_MARKER}\n"
    before = content.split(BEGIN_MARKER)[0]
    after = content.split(END_MARKER)[1]
    return f"{before}{BEGIN_MARKER}\n{generated}\n{END_MARKER}{after}"


def sync_all(write: bool = False) -> list[str]:
    diffs = []
    catalog = load_catalog()
    version = get_version()

    # 1. Root README.md
    if README_PATH.is_file():
        readme_content = README_PATH.read_text(encoding="utf-8")
        catalog_md = render_root_catalog_markdown(catalog)
        new_readme = update_markdown_section(readme_content, catalog_md)
        if new_readme != readme_content:
            diffs.append("README.md catalog section is out of sync")
            if write:
                README_PATH.write_text(new_readme, encoding="utf-8")

    # 2. Engineering README.md
    eng_readme_content = render_engineering_readme(catalog)
    current_eng = ENG_README_PATH.read_text(encoding="utf-8") if ENG_README_PATH.is_file() else ""
    if current_eng != eng_readme_content:
        diffs.append("skills/engineering/README.md is out of sync")
        if write:
            ENG_README_PATH.parent.mkdir(parents=True, exist_ok=True)
            ENG_README_PATH.write_text(eng_readme_content, encoding="utf-8")

    # 3. .claude-plugin/plugin.json
    plugin_content = generate_plugin_json(catalog, version)
    current_plugin = PLUGIN_JSON_PATH.read_text(encoding="utf-8") if PLUGIN_JSON_PATH.is_file() else ""
    if current_plugin != plugin_content:
        diffs.append(".claude-plugin/plugin.json is out of sync")
        if write:
            PLUGIN_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            PLUGIN_JSON_PATH.write_text(plugin_content, encoding="utf-8")

    # 4. .claude-plugin/marketplace.json
    marketplace_content = generate_marketplace_json(version)
    current_marketplace = MARKETPLACE_JSON_PATH.read_text(encoding="utf-8") if MARKETPLACE_JSON_PATH.is_file() else ""
    if current_marketplace != marketplace_content:
        diffs.append(".claude-plugin/marketplace.json is out of sync")
        if write:
            MARKETPLACE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            MARKETPLACE_JSON_PATH.write_text(marketplace_content, encoding="utf-8")

    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize catalog-derived files.")
    parser.add_argument("--write", action="store_true", help="Write changes to disk")
    parser.add_argument("--check", action="store_true", help="Check if files are synchronized")
    args = parser.parse_args()

    if not args.write and not args.check:
        parser.error("Must specify either --write or --check")

    if args.write:
        diffs = sync_all(write=True)
        if diffs:
            print(f"Updated {len(diffs)} surface(s).")
        else:
            print("All surfaces are already synchronized.")
        return 0

    if args.check:
        diffs = sync_all(write=False)
        if diffs:
            print("Catalog synchronization check failed. The following surfaces are out of sync:", file=sys.stderr)
            for d in diffs:
                print(f"  - {d}", file=sys.stderr)
            return 1
        print("Catalog synchronization check passed.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
