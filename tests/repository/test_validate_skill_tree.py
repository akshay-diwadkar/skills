from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import validate_repository as validator  # noqa: E402

LOCKED_SKILLS = {"create-diagram", "github-issue-planner"}


def test_validate_repository_passes_cleanly() -> None:
    assert validator.main() == 0


def test_skills_lock_validation_passes() -> None:
    assert validator.validate_skills_lock() == []
