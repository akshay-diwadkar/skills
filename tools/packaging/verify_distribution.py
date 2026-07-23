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

    # Check for forbidden development files
    forbidden_names = {"browser_smoke.py", "conftest.py", "debug_hash.py"}
    for p in dist_path.rglob("*"):
        if p.name in forbidden_names or p.name.startswith("test_") or "evals" in p.parts or "tests" in p.parts:
            errors.append(f"Distribution contains forbidden development artifact: {p.relative_to(dist_path)}")

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
