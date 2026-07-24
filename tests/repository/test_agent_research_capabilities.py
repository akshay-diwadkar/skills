from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import sync_catalog  # noqa: E402
from validate_repository import parse_yaml_frontmatter, validate_agent_discovery  # noqa: E402


def test_all_current_agents_declare_web_research_capability() -> None:
    agents_cat = sync_catalog.load_agents_catalog()
    agents = agents_cat.get("agents", [])
    assert len(agents) == 4
    for agent in agents:
        name = agent["name"]
        caps = agent.get("capabilities", {})
        assert caps.get("web_research") is True, f"Agent {name} missing web_research: true"


def test_claude_adapter_web_tools_and_permissions() -> None:
    agents_cat = sync_catalog.load_agents_catalog()
    for agent in agents_cat.get("agents", []):
        name = agent["name"]
        repo_write = agent.get("access", {}).get("repository_write", False)

        claude_file = REPO_ROOT / "agents" / "claude" / f"{name}.md"
        assert claude_file.is_file()
        claude_text = claude_file.read_text(encoding="utf-8")
        fm = parse_yaml_frontmatter(claude_text)
        tools = fm.get("tools", [])

        assert tools.count("WebSearch") == 1
        assert tools.count("WebFetch") == 1
        assert tools.index("WebSearch") < tools.index("WebFetch")

        if not repo_write:
            assert "Edit" not in tools
            assert "Write" not in tools
        else:
            assert "Edit" in tools
            assert "Write" in tools


def test_synthetic_agent_web_research_false_omits_web_tools() -> None:
    synthetic_agent = {
        "name": "test-agent",
        "summary": "Synthetic test agent",
        "source": "agents/source/architecture-engineer.md",
        "access": {"repository_write": False},
        "capabilities": {"web_research": False},
        "skills": ["create-diagram"],
    }
    adapter_text = sync_catalog.generate_claude_adapter(synthetic_agent)
    fm = parse_yaml_frontmatter(adapter_text)
    tools = fm.get("tools", [])

    assert "WebSearch" not in tools
    assert "WebFetch" not in tools


def test_cursor_and_codex_adapters_contain_policy_without_unsupported_keys() -> None:
    agents_cat = sync_catalog.load_agents_catalog()
    for agent in agents_cat.get("agents", []):
        name = agent["name"]

        # Cursor check
        cursor_file = REPO_ROOT / "agents" / "cursor" / f"{name}.md"
        assert cursor_file.is_file()
        cursor_text = cursor_file.read_text(encoding="utf-8")
        assert "## External Research Policy" in cursor_text
        fm = parse_yaml_frontmatter(cursor_text)
        assert "tools" not in fm

        # Codex check
        codex_file = REPO_ROOT / ".codex" / "agents" / f"{name}.toml"
        assert codex_file.is_file()
        with codex_file.open("rb") as f:
            codex_data = tomllib.load(f)
        assert "## External Research Policy" in codex_data["developer_instructions"]
        for forbidden_key in ("tools", "web_search", "network_access"):
            assert forbidden_key not in codex_data


def test_missing_or_invalid_web_research_capability_rejected() -> None:
    invalid_agents: list[dict[str, Any]] = [
        {"name": "no-caps", "summary": "No caps", "source": "agents/source/architecture-engineer.md"},
        {"name": "missing-web", "summary": "Missing web", "source": "agents/source/architecture-engineer.md", "capabilities": {}},
        {"name": "non-bool-web", "summary": "Non-bool web", "source": "agents/source/architecture-engineer.md", "capabilities": {"web_research": "true"}},
    ]

    for inv in invalid_agents:
        with pytest.raises(ValueError):
            sync_catalog.generate_claude_adapter(inv)

    malformed_catalog = {
        "schema_version": 1,
        "agents": [
            {
                "name": "bad-agent",
                "status": "stable",
                "summary": "Bad agent",
                "source": "agents/source/architecture-engineer.md",
                "documentation": "docs/agents/architecture-engineer.md",
                "access": {"repository_write": False, "artifact_write": True, "external_write": False},
                "capabilities": {},
            }
        ]
    }
    errors = validate_agent_discovery(malformed_catalog)
    assert any("must define boolean 'capabilities.web_research'" in err for err in errors)
