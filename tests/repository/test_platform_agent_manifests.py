from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "tools" / "validation" / "schemas"

sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))
import sync_catalog  # noqa: E402


def test_platform_manifests_validity_and_version_sync() -> None:
    version = sync_catalog.get_version()
    agents_cat = sync_catalog.load_agents_catalog()
    skills_cat = sync_catalog.load_skills_catalog()

    # Load schemas
    claude_plugin_schema = json.loads((SCHEMAS_DIR / "claude_plugin_schema.json").read_text(encoding="utf-8"))
    claude_market_schema = json.loads((SCHEMAS_DIR / "claude_marketplace_schema.json").read_text(encoding="utf-8"))
    cursor_plugin_schema = json.loads((SCHEMAS_DIR / "cursor_plugin_schema.json").read_text(encoding="utf-8"))
    cursor_market_schema = json.loads((SCHEMAS_DIR / "cursor_marketplace_schema.json").read_text(encoding="utf-8"))

    # 1. Claude plugin & marketplace manifests
    claude_plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    assert claude_plugin.is_file()
    claude_data = json.loads(claude_plugin.read_text(encoding="utf-8"))
    jsonschema.validate(instance=claude_data, schema=claude_plugin_schema)
    assert claude_data["version"] == version
    assert claude_data["name"] == "engineering-skills"
    assert claude_data["author"]["name"] == "akshay-diwadkar"
    assert "publisher" not in claude_data
    assert claude_data["license"] == "MIT"
    assert (REPO_ROOT / claude_data["agents"].lstrip("./")).is_dir()
    for sk_path in claude_data["skills"]:
        assert sk_path.startswith("./")
        real_path = REPO_ROOT / sk_path.lstrip("./")
        assert real_path.is_dir()
        assert (real_path / "SKILL.md").is_file()

    claude_market = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    assert claude_market.is_file()
    claude_market_data = json.loads(claude_market.read_text(encoding="utf-8"))
    jsonschema.validate(instance=claude_market_data, schema=claude_market_schema)
    assert claude_market_data["owner"]["name"] == "akshay-diwadkar"
    assert len(claude_market_data["plugins"]) > 0
    assert claude_market_data["plugins"][0]["version"] == version
    assert "description" in claude_market_data["plugins"][0]

    # 2. Cursor plugin & marketplace manifests
    cursor_plugin = REPO_ROOT / ".cursor-plugin" / "plugin.json"
    assert cursor_plugin.is_file()
    cursor_data = json.loads(cursor_plugin.read_text(encoding="utf-8"))
    jsonschema.validate(instance=cursor_data, schema=cursor_plugin_schema)
    assert cursor_data["version"] == version
    assert cursor_data["name"] == "engineering-skills"
    assert cursor_data["publisher"] == "akshay-diwadkar"
    assert cursor_data["license"] == "MIT"
    assert isinstance(cursor_data["skills"], list)
    for sk_path in cursor_data["skills"]:
        assert sk_path.startswith("./")
        real_path = REPO_ROOT / sk_path.lstrip("./")
        assert real_path.is_dir()
        assert (real_path / "SKILL.md").is_file()

    cursor_market = REPO_ROOT / ".cursor-plugin" / "marketplace.json"
    assert cursor_market.is_file()
    cursor_market_data = json.loads(cursor_market.read_text(encoding="utf-8"))
    jsonschema.validate(instance=cursor_market_data, schema=cursor_market_schema)
    assert cursor_market_data["owner"]["name"] == "akshay-diwadkar"
    assert len(cursor_market_data["plugins"]) > 0

    # Assert Cursor marketplace entry does NOT include unsupported 'version' field
    assert "version" not in cursor_market_data["plugins"][0]

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

    # 4. Prove all catalogued stable/beta skills are discoverable
    catalog_skills = {
        f"./{s['path']}" for s in skills_cat.get("skills", []) if s.get("status") in ("stable", "beta")
    }
    assert catalog_skills.issubset(set(claude_data["skills"]))
    assert catalog_skills.issubset(set(cursor_data["skills"]))


def test_platform_schema_rejection_of_invalid_shapes() -> None:
    claude_plugin_schema = json.loads((SCHEMAS_DIR / "claude_plugin_schema.json").read_text(encoding="utf-8"))
    cursor_market_schema = json.loads((SCHEMAS_DIR / "cursor_marketplace_schema.json").read_text(encoding="utf-8"))

    # Invalid: Claude plugin with unsupported 'publisher' key instead of 'author'
    bad_claude = {
        "name": "engineering-skills",
        "version": "1.0.0",
        "description": "test",
        "publisher": "akshay",
        "license": "MIT",
        "skills": ["./skills/engineering/plan-with-senior-dev"],
        "agents": "./agents/claude/",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_claude, schema=claude_plugin_schema)

    # Invalid: Cursor marketplace with unsupported 'version' field in plugin list
    bad_cursor_market = {
        "name": "engineering-skills-marketplace",
        "owner": {"name": "akshay"},
        "plugins": [
            {
                "name": "engineering-skills",
                "version": "1.0.0",
                "description": "test",
                "source": "./",
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_cursor_market, schema=cursor_market_schema)

