#!/usr/bin/env python3
"""Synchronize or check catalog-derived repository surfaces."""

from __future__ import annotations

import argparse
import json
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
VERSION_PATH = ROOT / "VERSION"
README_PATH = ROOT / "README.md"
ENG_README_PATH = ROOT / "skills" / "engineering" / "README.md"
DOCS_AGENTS_PATH = ROOT / "docs" / "agents.md"
CLAUDE_PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
CURSOR_PLUGIN_JSON = ROOT / ".cursor-plugin" / "plugin.json"
CURSOR_MARKETPLACE_JSON = ROOT / ".cursor-plugin" / "marketplace.json"
CODEX_CONFIG_TOML = ROOT / ".codex" / "config.toml"

BEGIN_SKILL_MARKER = "<!-- BEGIN GENERATED SKILL CATALOG -->"
END_SKILL_MARKER = "<!-- END GENERATED SKILL CATALOG -->"
BEGIN_AGENT_MARKER = "<!-- BEGIN GENERATED AGENT CATALOG -->"
END_AGENT_MARKER = "<!-- END GENERATED AGENT CATALOG -->"


def get_version() -> str:
    if not VERSION_PATH.is_file():
        return "1.0.0"
    return VERSION_PATH.read_text(encoding="utf-8").strip()


def load_skills_catalog() -> dict[str, Any]:
    with SKILLS_CATALOG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_agents_catalog() -> dict[str, Any]:
    if not AGENTS_CATALOG_PATH.is_file():
        return {"schema_version": 1, "agents": []}
    with AGENTS_CATALOG_PATH.open("r", encoding="utf-8") as f:
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


def render_root_agents_catalog_markdown(agents_catalog: dict[str, Any]) -> str:
    lines = [
        "| Agent | Status | Access (Repo/Art/Ext) | Skills | Summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for agent in agents_catalog.get("agents", []):
        name = agent["name"]
        status = agent["status"]
        acc = agent.get("access", {})
        access_str = f"Repo:{acc.get('repository_write', False)} / Art:{acc.get('artifact_write', False)} / Ext:{acc.get('external_write', False)}"
        skills_str = ", ".join(f"`{s}`" for s in agent.get("skills", []))
        summary = agent["summary"]
        doc = agent.get("documentation", f"docs/agents/{name}.md")
        lines.append(f"| [{name}]({doc}) | `{status}` | `{access_str}` | {skills_str} | {summary} |")
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


def render_docs_agents_markdown(agents_catalog: dict[str, Any]) -> str:
    lines = [
        "# Engineering Agents Overview",
        "",
        "Agents are focused, role-based orchestration layers built on top of canonical engineering skills.",
        "",
        "## Platform Support & Distribution Matrix",
        "",
        "| Platform | Skills Distributed | Agents Distributed | Scope |",
        "| --- | ---: | ---: | --- |",
        "| Claude Code plugin | Yes | Yes | Installed plugin |",
        "| Cursor plugin | Yes | Yes | Installed plugin |",
        "| Codex skill installation | Yes | No automatic custom-agent installation | Installed skills |",
        "| Codex repository clone | Yes | Yes | Current project |",
        "| Codex explicit installer | Existing installed skills | Yes | Selected target project |",
        "",
        "## Available Agents",
        "",
        "| Agent | Status | Repo Write | Web Research | Skills Included | Summary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for agent in agents_catalog.get("agents", []):
        name = agent["name"]
        status = agent["status"]
        repo_write = agent.get("access", {}).get("repository_write", False)
        web_res = agent.get("capabilities", {}).get("web_research", False)
        skills_str = ", ".join(f"`{s}`" for s in agent.get("skills", []))
        summary = agent["summary"]
        doc_link = f"./agents/{name}.md"
        lines.append(f"| [{name}]({doc_link}) | `{status}` | `{repo_write}` | `{web_res}` | {skills_str} | {summary} |")

    lines.append("")
    return "\n".join(lines)


def generate_claude_adapter(agent: dict[str, Any]) -> str:
    name = agent["name"]
    summary = agent["summary"]
    skills = agent.get("skills", [])
    repo_write = agent.get("access", {}).get("repository_write", False)

    capabilities = agent.get("capabilities")
    if capabilities is None or not isinstance(capabilities, dict) or "web_research" not in capabilities or not isinstance(capabilities.get("web_research"), bool):
        raise ValueError(f"Agent '{name}' requires a valid boolean 'capabilities.web_research' field")

    web_research = capabilities["web_research"]

    tools = ["Read", "Grep", "Glob", "Bash"]
    if web_research:
        tools.extend(["WebSearch", "WebFetch"])
    tools.append("Skill")
    if repo_write:
        tools.extend(["Edit", "Write"])

    source_path = ROOT / agent["source"]
    source_body = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""

    fm = [
        "---",
        f"name: {name}",
        f"description: {summary}",
        "model: inherit",
        "effort: high",
        "maxTurns: 40",
        "tools:",
    ]
    for t in tools:
        fm.append(f"  - {t}")
    fm.append("skills:")
    for s in skills:
        fm.append(f"  - {s}")
    fm.append("---")
    fm.append(f"<!-- Generated from catalog/agents.yaml and {agent['source']}. Do not edit directly. -->")
    fm.append("")
    fm.append(source_body.strip())
    fm.append("")

    return "\n".join(fm)


def generate_cursor_adapter(agent: dict[str, Any]) -> str:
    name = agent["name"]
    summary = agent["summary"]
    repo_write = agent.get("access", {}).get("repository_write", False)

    source_path = ROOT / agent["source"]
    source_body = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""

    fm = [
        "---",
        f"name: {name}",
        f"description: {summary}",
        "model: inherit",
        f"readonly: {str(not repo_write).lower()}",
        "---",
        f"<!-- Generated from catalog/agents.yaml and {agent['source']}. Do not edit directly. -->",
        "",
        source_body.strip(),
        "",
    ]
    return "\n".join(fm)


def generate_codex_adapter(agent: dict[str, Any]) -> str:
    name = agent["name"]
    summary = agent["summary"]
    repo_write = agent.get("access", {}).get("repository_write", False)
    sandbox_mode = "workspace-write" if repo_write else "read-only"

    source_path = ROOT / agent["source"]
    source_body = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""

    # Triple quote escaping for TOML
    escaped_summary = summary.replace('"""', '\\"\\"\\"')
    escaped_body = source_body.strip().replace('"""', '\\"\\"\\"')

    toml_lines = [
        f'# Generated from catalog/agents.yaml and {agent["source"]}. Do not edit directly.',
        f'name = "{name}"',
        'description = """',
        escaped_summary,
        '"""',
        "",
        'model_reasoning_effort = "high"',
        f'sandbox_mode = "{sandbox_mode}"',
        "",
        'developer_instructions = """',
        escaped_body,
        '"""',
        "",
    ]
    return "\n".join(toml_lines)


def generate_claude_plugin_json(skills_catalog: dict[str, Any], version: str) -> str:
    promoted_skills = [
        s["path"]
        for s in skills_catalog.get("skills", [])
        if s.get("status") in ("stable", "beta") and s.get("platforms", {}).get("claude_plugin", True)
    ]
    data = {
        "name": "engineering-skills",
        "version": version,
        "description": "Production engineering skills monorepo for software architecture, planning, implementation, auditing, and optimization.",
        "publisher": "akshay-diwadkar",
        "license": "MIT",
        "skills": promoted_skills,
        "agents": "./agents/claude/"
    }
    return json.dumps(data, indent=2) + "\n"


def generate_cursor_plugin_json(version: str) -> str:
    data = {
        "name": "engineering-skills",
        "displayName": "Engineering Skills",
        "version": version,
        "description": "Production engineering skills and focused engineering agents.",
        "publisher": "akshay-diwadkar",
        "license": "MIT",
        "skills": "./skills/",
        "agents": "./agents/cursor/"
    }
    return json.dumps(data, indent=2) + "\n"


def generate_marketplace_json(version: str) -> str:
    data = {
        "name": "engineering-skills-marketplace",
        "plugins": [
            {
                "name": "engineering-skills",
                "version": version,
                "description": "Production engineering skills monorepo for software architecture, planning, implementation, auditing, and optimization.",
                "source": "./"
            }
        ]
    }
    return json.dumps(data, indent=2) + "\n"


def generate_codex_config_toml() -> str:
    return '[agents]\nmax_concurrent_threads_per_session = 4\n'


def update_markdown_section(content: str, begin_marker: str, end_marker: str, generated: str) -> str:
    if begin_marker not in content or end_marker not in content:
        return content.rstrip() + f"\n\n{begin_marker}\n{generated}\n{end_marker}\n"
    before = content.split(begin_marker)[0]
    after = content.split(end_marker)[1]
    return f"{before}{begin_marker}\n{generated}\n{end_marker}{after}"


def sync_all(write: bool = False) -> list[str]:
    diffs = []
    skills_catalog = load_skills_catalog()
    agents_catalog = load_agents_catalog()
    version = get_version()

    # 1. Root README.md (Skills & Agents sections)
    if README_PATH.is_file():
        readme_content = README_PATH.read_text(encoding="utf-8")
        skills_md = render_root_skills_catalog_markdown(skills_catalog)
        agents_md = render_root_agents_catalog_markdown(agents_catalog)

        new_readme = update_markdown_section(readme_content, BEGIN_SKILL_MARKER, END_SKILL_MARKER, skills_md)
        new_readme = update_markdown_section(new_readme, BEGIN_AGENT_MARKER, END_AGENT_MARKER, agents_md)

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

    # 3. docs/agents.md
    docs_agents_content = render_docs_agents_markdown(agents_catalog)
    current_docs_agents = DOCS_AGENTS_PATH.read_text(encoding="utf-8") if DOCS_AGENTS_PATH.is_file() else ""
    if current_docs_agents != docs_agents_content:
        diffs.append("docs/agents.md out of sync")
        if write:
            DOCS_AGENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            DOCS_AGENTS_PATH.write_text(docs_agents_content, encoding="utf-8")

    # 4. Agent Adapters (Claude, Cursor, Codex)
    for agent in agents_catalog.get("agents", []):
        name = agent["name"]

        # Claude adapter
        claude_content = generate_claude_adapter(agent)
        claude_path = ROOT / "agents" / "claude" / f"{name}.md"
        current_claude = claude_path.read_text(encoding="utf-8") if claude_path.is_file() else ""
        if current_claude != claude_content:
            diffs.append(f"agents/claude/{name}.md out of sync")
            if write:
                claude_path.parent.mkdir(parents=True, exist_ok=True)
                claude_path.write_text(claude_content, encoding="utf-8")

        # Cursor adapter
        cursor_content = generate_cursor_adapter(agent)
        cursor_path = ROOT / "agents" / "cursor" / f"{name}.md"
        current_cursor = cursor_path.read_text(encoding="utf-8") if cursor_path.is_file() else ""
        if current_cursor != cursor_content:
            diffs.append(f"agents/cursor/{name}.md out of sync")
            if write:
                cursor_path.parent.mkdir(parents=True, exist_ok=True)
                cursor_path.write_text(cursor_content, encoding="utf-8")

        # Codex adapter
        codex_content = generate_codex_adapter(agent)
        codex_path = ROOT / ".codex" / "agents" / f"{name}.toml"
        current_codex = codex_path.read_text(encoding="utf-8") if codex_path.is_file() else ""
        if current_codex != codex_content:
            diffs.append(f".codex/agents/{name}.toml out of sync")
            if write:
                codex_path.parent.mkdir(parents=True, exist_ok=True)
                codex_path.write_text(codex_content, encoding="utf-8")

    # 5. Manifests
    claude_plugin = generate_claude_plugin_json(skills_catalog, version)
    current_claude_plugin = CLAUDE_PLUGIN_JSON.read_text(encoding="utf-8") if CLAUDE_PLUGIN_JSON.is_file() else ""
    if current_claude_plugin != claude_plugin:
        diffs.append(".claude-plugin/plugin.json out of sync")
        if write:
            CLAUDE_PLUGIN_JSON.parent.mkdir(parents=True, exist_ok=True)
            CLAUDE_PLUGIN_JSON.write_text(claude_plugin, encoding="utf-8")

    claude_market = generate_marketplace_json(version)
    current_claude_market = CLAUDE_MARKETPLACE_JSON.read_text(encoding="utf-8") if CLAUDE_MARKETPLACE_JSON.is_file() else ""
    if current_claude_market != claude_market:
        diffs.append(".claude-plugin/marketplace.json out of sync")
        if write:
            CLAUDE_MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
            CLAUDE_MARKETPLACE_JSON.write_text(claude_market, encoding="utf-8")

    cursor_plugin = generate_cursor_plugin_json(version)
    current_cursor_plugin = CURSOR_PLUGIN_JSON.read_text(encoding="utf-8") if CURSOR_PLUGIN_JSON.is_file() else ""
    if current_cursor_plugin != cursor_plugin:
        diffs.append(".cursor-plugin/plugin.json out of sync")
        if write:
            CURSOR_PLUGIN_JSON.parent.mkdir(parents=True, exist_ok=True)
            CURSOR_PLUGIN_JSON.write_text(cursor_plugin, encoding="utf-8")

    cursor_market = generate_marketplace_json(version)
    current_cursor_market = CURSOR_MARKETPLACE_JSON.read_text(encoding="utf-8") if CURSOR_MARKETPLACE_JSON.is_file() else ""
    if current_cursor_market != cursor_market:
        diffs.append(".cursor-plugin/marketplace.json out of sync")
        if write:
            CURSOR_MARKETPLACE_JSON.parent.mkdir(parents=True, exist_ok=True)
            CURSOR_MARKETPLACE_JSON.write_text(cursor_market, encoding="utf-8")

    codex_config = generate_codex_config_toml()
    current_codex_config = CODEX_CONFIG_TOML.read_text(encoding="utf-8") if CODEX_CONFIG_TOML.is_file() else ""
    if current_codex_config != codex_config:
        diffs.append(".codex/config.toml out of sync")
        if write:
            CODEX_CONFIG_TOML.parent.mkdir(parents=True, exist_ok=True)
            CODEX_CONFIG_TOML.write_text(codex_config, encoding="utf-8")

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
