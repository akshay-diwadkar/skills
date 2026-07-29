from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import run_mypy  # noqa: E402
import validate_repository as validator  # noqa: E402

CANONICAL_SKILL_NAMES = {
    "audit-codebase",
    "design-codebase",
    "diagram-codebase",
    "implement-plan",
    "map-codebase",
    "optimize-codebase",
    "plan-change",
    "scope-issue",
}


def test_repository_validation_passes() -> None:
    assert validator.main() == 0


def test_skill_discovery_matches_expected_directories() -> None:
    skills = validator.discover_skills()
    assert {skill.name for skill in skills} == CANONICAL_SKILL_NAMES


def test_skill_metadata_and_tracked_references_use_canonical_names_only() -> None:
    """Reject retired naming families outside explicit migration compatibility code."""
    patterns = (
        re.compile(r"\b[a-z]+-with-senior-dev\b"),
        re.compile(r"\bcodebase-issue-[a-z]+\b"),
        re.compile(r"\bgithub" + r"-issue-planner\b"),
        re.compile(r"\bcreate" + r"-diagram\b"),
    )
    retired_map_codebase_names = (
        "build" + "-codebase-knowledge",
        "BUILD" + "-CODEBASE-KNOWLEDGE",
        "build" + "_codebase_knowledge",
        "Build" + " Codebase Knowledge",
    )
    allowed_legacy_locations = {
        "skills/engineering/map-codebase/scripts/scaffold_github_workflow.py",
        "skills/engineering/map-codebase/scripts/link_agent_docs.py",
        "tests/skills/map-codebase/test_scaffold_github_workflow.py",
        "tests/skills/map-codebase/test_agent_docs_managed_block.py",
    }

    for skill in validator.discover_skills():
        frontmatter = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
        name = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
        assert name is not None
        assert name.group(1).strip() in CANONICAL_SKILL_NAMES

    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".pytest_cache" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert not any(pattern.search(text) for pattern in patterns), path.relative_to(REPO_ROOT)
        if any(name in text for name in retired_map_codebase_names):
            assert path.relative_to(REPO_ROOT).as_posix() in allowed_legacy_locations


def test_skill_packages_have_no_platform_metadata() -> None:
    assert all(not (skill / "agents").exists() for skill in validator.discover_skills())
    assert validator.validate_retired_surfaces() == []


def test_pipeline_readmes_and_skill_changelog_are_supported_resources() -> None:
    engineering = REPO_ROOT / "skills" / "engineering"
    for skill_name in ("design-codebase", "plan-change", "scope-issue"):
        assert not validator.validate_skill_package(engineering / skill_name)
        assert (engineering / skill_name / "README.md").is_file()
    assert (engineering / "design-codebase" / "CHANGELOG.md").is_file()


def test_mypy_scopes_are_discovered_from_skill_directories() -> None:
    assert {name for name, _, _ in run_mypy.discover_skill_scopes()} == {skill.name for skill in validator.discover_skills()}
