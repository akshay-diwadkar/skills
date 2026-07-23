from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import validate_repository  # noqa: E402


def test_validate_agent_discovery_fails_on_broken_agent_catalog() -> None:
    fake_catalog = {
        "agents": [
            {
                "name": "nonexistent-agent",
                "source": "agents/source/nonexistent.md",
                "documentation": "docs/agents/nonexistent.md",
                "capabilities": {"web_research": True},
            }
        ]
    }
    errors = validate_repository.validate_agent_discovery(fake_catalog)
    assert len(errors) > 0, "validate_agent_discovery must fail when an agent catalog entry is broken or missing files"
