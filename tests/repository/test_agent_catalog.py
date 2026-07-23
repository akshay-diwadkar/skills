from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))

import validate_catalog  # noqa: E402


def test_agents_catalog_validates_cleanly() -> None:
    skills_cat, skills_errors = validate_catalog.validate_skills_catalog()
    assert skills_errors == [], f"Skills catalog errors: {skills_errors}"

    agent_errors = validate_catalog.validate_agents_catalog(skills_cat)
    assert agent_errors == [], f"Agents catalog errors: {agent_errors}"


def test_all_four_canonical_agents_present() -> None:
    skills_cat, _ = validate_catalog.validate_skills_catalog()
    agents_cat = validate_catalog.load_yaml(REPO_ROOT / "catalog" / "agents.yaml")
    agents = agents_cat.get("agents", [])
    agent_names = {a["name"] for a in agents}

    expected = {
        "architecture-engineer",
        "delivery-engineer",
        "issue-resolution-engineer",
        "codebase-health-engineer",
    }
    assert agent_names == expected
