from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))

import sync_catalog  # noqa: E402


def test_agent_skill_references_exist_and_support_model_invocation() -> None:
    skills_cat = sync_catalog.load_skills_catalog()
    agents_cat = sync_catalog.load_agents_catalog()

    known_skills = {s["name"]: s for s in skills_cat.get("skills", [])}

    for agent in agents_cat.get("agents", []):
        agent_name = agent["name"]
        for skill_name in agent.get("skills", []):
            assert skill_name in known_skills, f"Agent {agent_name} references unknown skill {skill_name}"
            skill = known_skills[skill_name]
            assert skill.get("invocation") in ("model", "both"), (
                f"Agent {agent_name} references skill {skill_name} with non-model invocation '{skill.get('invocation')}'"
            )
