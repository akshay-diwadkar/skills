from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))

import sync_catalog  # noqa: E402


def test_platform_manifests_validity_and_version_sync() -> None:
    version = sync_catalog.get_version()
    agents_cat = sync_catalog.load_agents_catalog()

    # 1. Claude plugin & marketplace manifests
    claude_plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    assert claude_plugin.is_file()
    claude_data = json.loads(claude_plugin.read_text(encoding="utf-8"))
    assert claude_data["version"] == version
    assert claude_data["name"] == "engineering-skills"
    assert claude_data["publisher"] == "akshay-diwadkar"
    assert claude_data["license"] == "MIT"
    assert (REPO_ROOT / claude_data["agents"].lstrip("./")).is_dir()
    for sk_path in claude_data["skills"]:
        assert (REPO_ROOT / sk_path).is_dir()
        assert (REPO_ROOT / sk_path / "SKILL.md").is_file()

    claude_market = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    assert claude_market.is_file()
    claude_market_data = json.loads(claude_market.read_text(encoding="utf-8"))
    assert len(claude_market_data["plugins"]) > 0
    assert claude_market_data["plugins"][0]["version"] == version
    assert "description" in claude_market_data["plugins"][0]

    # 2. Cursor plugin & marketplace manifests
    cursor_plugin = REPO_ROOT / ".cursor-plugin" / "plugin.json"
    assert cursor_plugin.is_file()
    cursor_data = json.loads(cursor_plugin.read_text(encoding="utf-8"))
    assert cursor_data["version"] == version
    assert cursor_data["name"] == "engineering-skills"
    assert cursor_data["publisher"] == "akshay-diwadkar"
    assert cursor_data["license"] == "MIT"
    assert (REPO_ROOT / cursor_data["skills"].lstrip("./")).is_dir()
    assert (REPO_ROOT / cursor_data["agents"].lstrip("./")).is_dir()

    cursor_market = REPO_ROOT / ".cursor-plugin" / "marketplace.json"
    assert cursor_market.is_file()
    cursor_market_data = json.loads(cursor_market.read_text(encoding="utf-8"))
    assert len(cursor_market_data["plugins"]) > 0
    assert cursor_market_data["plugins"][0]["version"] == version

    # 3. Codex config & agent TOML files
    codex_config = REPO_ROOT / ".codex" / "config.toml"
    assert codex_config.is_file()
    config_data = tomllib.loads(codex_config.read_text(encoding="utf-8"))
    assert "agents" in config_data

    codex_agents_dir = REPO_ROOT / ".codex" / "agents"
    assert codex_agents_dir.is_dir()
    for agent in agents_cat.get("agents", []):
        name = agent["name"]
        adapter_file = codex_agents_dir / f"{name}.toml"
        assert adapter_file.is_file()
        agent_toml = tomllib.loads(adapter_file.read_text(encoding="utf-8"))
        assert agent_toml["name"] == name
        assert "developer_instructions" in agent_toml
        assert "sandbox_mode" in agent_toml
