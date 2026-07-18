from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / ".github" / "scripts" / "validate_skill_tree.py"
SPEC = importlib.util.spec_from_file_location("validate_skill_tree", VALIDATOR_PATH)
assert SPEC is not None
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


LOCKED_SKILLS = {"create-diagram", "github-issue-planner"}


@pytest.mark.parametrize(
    "path",
    [
        "create-diagram/test/test_diagram_tools.py",
        "create-diagram/evals/case.json",
        "create-diagram/fixtures/complex.json",
        "github-issue-planner/scripts/test_fetch_github_issues.py",
        "github-issue-planner/scripts/score_audit.py",
        "create-diagram/scripts/browser_smoke.py",
        "create-diagram/scripts/check_template_refs.py",
        "create-diagram/scripts/debug_hash.py",
    ],
)
def test_rejects_development_artifacts_inside_locked_skills(path: str) -> None:
    assert validator.forbidden_skill_artifact(path, LOCKED_SKILLS)


@pytest.mark.parametrize(
    "path",
    [
        "tests/create-diagram/test_diagram_tools.py",
        "tests/create-diagram/fixtures/complex.json",
        "tests/github-issue-planner/test_fetch_github_issues.py",
    ],
)
def test_allows_repository_level_development_harnesses(path: str) -> None:
    assert not validator.forbidden_skill_artifact(path, LOCKED_SKILLS)


@pytest.mark.parametrize(
    "path",
    [
        "create-diagram/SKILL.md",
        "create-diagram/assets/geometry-config.json",
        "create-diagram/scripts/build_diagram.py",
        "github-issue-planner/scripts/fetch_github_issues.py",
    ],
)
def test_allows_runtime_skill_resources(path: str) -> None:
    assert not validator.forbidden_skill_artifact(path, LOCKED_SKILLS)


def test_reports_every_forbidden_skill_artifact() -> None:
    paths = [
        "create-diagram/scripts/build_diagram.py",
        "create-diagram/test/test_diagram_tools.py",
        "github-issue-planner/scripts/debug_hash.py",
        "tests/create-diagram/test_diagram_tools.py",
    ]

    assert validator.validate_skill_distribution(paths, LOCKED_SKILLS) == [
        "development artifact inside distributable skill: create-diagram/test/test_diagram_tools.py",
        "development artifact inside distributable skill: github-issue-planner/scripts/debug_hash.py",
    ]


def test_runtime_file_counts_report_mismatches() -> None:
    paths = [
        "create-diagram/SKILL.md",
        "create-diagram/scripts/build_diagram.py",
        "github-issue-planner/SKILL.md",
    ]

    assert validator.validate_runtime_file_counts(
        paths,
        {"create-diagram": 2, "github-issue-planner": 2},
    ) == ["github-issue-planner: expected 2 runtime files, found 1"]
