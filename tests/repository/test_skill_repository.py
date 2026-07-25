from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import run_mypy  # noqa: E402
import validate_repository as validator  # noqa: E402


def test_repository_validation_passes() -> None:
    assert validator.main() == 0


def test_skill_discovery_matches_expected_directories() -> None:
    skills = validator.discover_skills()
    assert {skill.name for skill in skills} == {
        "build-codebase-knowledge",
        "codebase-issue-auditor",
        "create-diagram",
        "design-codebase-with-senior-dev",
        "github-issue-planner",
        "implement-with-senior-dev",
        "optimize-codebase-with-senior-dev",
        "plan-with-senior-dev",
    }


def test_skill_packages_have_no_platform_metadata() -> None:
    assert all(not (skill / "agents").exists() for skill in validator.discover_skills())
    assert validator.validate_retired_surfaces() == []


def test_mypy_scopes_are_discovered_from_skill_directories() -> None:
    assert {name for name, _, _ in run_mypy.discover_skill_scopes()} == {skill.name for skill in validator.discover_skills()}
