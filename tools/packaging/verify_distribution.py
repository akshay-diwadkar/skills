#!/usr/bin/env python3
"""Verify built distribution tree for runtime completeness and clean boundaries."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "packaging"))

from build_distribution import build_distribution  # noqa: E402


def verify_distribution_tree(dist_path: Path) -> list[str]:
    errors = []

    # Ensure plugin manifests exist
    claude_json = dist_path / ".claude-plugin" / "plugin.json"
    if not claude_json.is_file():
        errors.append("Distribution missing .claude-plugin/plugin.json")

    claude_market = dist_path / ".claude-plugin" / "marketplace.json"
    if not claude_market.is_file():
        errors.append("Distribution missing .claude-plugin/marketplace.json")

    cursor_json = dist_path / ".cursor-plugin" / "plugin.json"
    if not cursor_json.is_file():
        errors.append("Distribution missing .cursor-plugin/plugin.json")

    cursor_market = dist_path / ".cursor-plugin" / "marketplace.json"
    if not cursor_market.is_file():
        errors.append("Distribution missing .cursor-plugin/marketplace.json")

    codex_config = dist_path / ".codex" / "config.toml"
    if not codex_config.is_file():
        errors.append("Distribution missing .codex/config.toml")

    license_file = dist_path / "LICENSE"
    if not license_file.is_file():
        errors.append("Distribution missing LICENSE")

    agents_dir = dist_path / "agents"
    if not agents_dir.is_dir():
        errors.append("Distribution missing agents directory")

    catalog_dir = dist_path / "catalog"
    if not catalog_dir.is_dir():
        errors.append("Distribution missing catalog directory")
    elif yaml:
        skills_yaml = catalog_dir / "skills.yaml"
        if not skills_yaml.is_file():
            errors.append("Distribution missing catalog/skills.yaml")
        else:
            with skills_yaml.open("r", encoding="utf-8") as f:
                cat_data = yaml.safe_load(f) or {}
            for s in cat_data.get("skills", []):
                s_path = dist_path / s["path"]
                if not s_path.is_dir():
                    errors.append(f"Distribution missing skill directory '{s['path']}'")
                elif not (s_path / "SKILL.md").is_file():
                    errors.append(f"Distribution missing SKILL.md for '{s['name']}' at {s['path']}")

        agents_yaml = catalog_dir / "agents.yaml"
        if not agents_yaml.is_file():
            errors.append("Distribution missing catalog/agents.yaml")
        else:
            with agents_yaml.open("r", encoding="utf-8") as f:
                agent_cat_data = yaml.safe_load(f) or {}
            for a in agent_cat_data.get("agents", []):
                a_name = a["name"]
                c_adapter = dist_path / "agents" / "claude" / f"{a_name}.md"
                if not c_adapter.is_file():
                    errors.append(f"Distribution missing Claude adapter for agent '{a_name}'")
                cur_adapter = dist_path / "agents" / "cursor" / f"{a_name}.md"
                if not cur_adapter.is_file():
                    errors.append(f"Distribution missing Cursor adapter for agent '{a_name}'")
                codex_adapter = dist_path / ".codex" / "agents" / f"{a_name}.toml"
                if not codex_adapter.is_file():
                    errors.append(f"Distribution missing Codex adapter for agent '{a_name}'")

    # Check Codex installer script
    codex_installer = dist_path / "tools" / "agents" / "install_codex_agents.py"
    if not codex_installer.is_file():
        errors.append("Distribution missing tools/agents/install_codex_agents.py")

    # Check for forbidden development files
    forbidden_names = {"browser_smoke.py", "conftest.py", "debug_hash.py"}
    for p in dist_path.rglob("*"):
        if p.name in forbidden_names or p.name.startswith("test_") or "evals" in p.parts or "tests" in p.parts:
            errors.append(f"Distribution contains forbidden development artifact: {p.relative_to(dist_path)}")

    # Validate all relative Markdown links in bundled distribution files
    import re
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    for md_file in dist_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for _, link in link_pattern.findall(content):
            link = link.strip()
            if not link or link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean_link = link.split("#")[0].strip()
            if not clean_link:
                continue

            target_path = (md_file.parent / clean_link).resolve()
            try:
                target_path.relative_to(dist_path.resolve())
            except ValueError:
                errors.append(f"{md_file.relative_to(dist_path)}: link target '{link}' points outside distribution bundle")
                continue

            if not target_path.exists():
                errors.append(f"{md_file.relative_to(dist_path)}: broken relative link target '{clean_link}'")

    # Validate end-user commands in README referencing repository files
    readme_path = dist_path / "README.md"
    if readme_path.is_file():
        readme_text = readme_path.read_text(encoding="utf-8")
        # Exclude Maintainer Verification section which contains source-repo maintainer commands
        user_readme_text = readme_text.split("## Maintainer Verification")[0]
        cmd_matches = re.findall(r"python\s+([A-Za-z0-9_/\\]+\.py)", user_readme_text)
        for cmd_path_str in cmd_matches:
            cmd_target = (dist_path / cmd_path_str).resolve()
            if not cmd_target.is_file():
                errors.append(f"README.md references missing command target file: {cmd_path_str}")

    return errors


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="verify-dist-"))
    try:
        dist_path = build_distribution(temp_dir)
        errors = verify_distribution_tree(dist_path)
        if errors:
            print("Distribution verification failed:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("Distribution verification passed.")
        return 0
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
