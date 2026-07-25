#!/usr/bin/env python3
"""Synchronize or check catalog-derived repository surfaces."""

from __future__ import annotations

import argparse
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
VERSION_PATH = ROOT / "VERSION"
README_PATH = ROOT / "README.md"
ENG_README_PATH = ROOT / "skills" / "engineering" / "README.md"

BEGIN_SKILL_MARKER = "<!-- BEGIN GENERATED SKILL CATALOG -->"
END_SKILL_MARKER = "<!-- END GENERATED SKILL CATALOG -->"


def get_version() -> str:
    if not VERSION_PATH.is_file():
        return "1.0.0"
    return VERSION_PATH.read_text(encoding="utf-8").strip()


def load_skills_catalog() -> dict[str, Any]:
    with SKILLS_CATALOG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_root_skills_catalog_markdown(catalog: dict[str, Any]) -> str:
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


def render_engineering_readme(catalog: dict[str, Any]) -> str:
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


def update_markdown_section(content: str, begin_marker: str, end_marker: str, generated: str) -> str:
    if begin_marker not in content or end_marker not in content:
        return content.rstrip() + f"\n\n{begin_marker}\n{generated}\n{end_marker}\n"
    before = content.split(begin_marker)[0]
    after = content.split(end_marker)[1]
    return f"{before}{begin_marker}\n{generated}\n{end_marker}{after}"


def sync_all(write: bool = False) -> list[str]:
    diffs = []
    skills_catalog = load_skills_catalog()

    # 1. Root README.md (Skills section)
    if README_PATH.is_file():
        readme_content = README_PATH.read_text(encoding="utf-8")
        skills_md = render_root_skills_catalog_markdown(skills_catalog)

        new_readme = update_markdown_section(readme_content, BEGIN_SKILL_MARKER, END_SKILL_MARKER, skills_md)

        if new_readme != readme_content:
            diffs.append("README.md catalog sections out of sync")
            if write:
                README_PATH.write_text(new_readme, encoding="utf-8")

    # 2. Engineering README.md
    eng_readme_content = render_engineering_readme(skills_catalog)
    current_eng = ENG_README_PATH.read_text(encoding="utf-8") if ENG_README_PATH.is_file() else ""
    if current_eng != eng_readme_content:
        diffs.append("skills/engineering/README.md out of sync")
        if write:
            ENG_README_PATH.parent.mkdir(parents=True, exist_ok=True)
            ENG_README_PATH.write_text(eng_readme_content, encoding="utf-8")

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
