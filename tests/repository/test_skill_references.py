from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))

import sync_catalog  # noqa: E402
import validate_repository  # noqa: E402


def test_runtime_skill_and_agent_references_are_valid() -> None:
    skills_catalog = sync_catalog.load_skills_catalog()
    agents_catalog = sync_catalog.load_agents_catalog()

    errors = validate_repository.validate_skill_references(skills_catalog, agents_catalog)
    assert not errors, "Unresolved skill reference errors found:\n" + "\n".join(errors)
