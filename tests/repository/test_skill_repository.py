from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import run_mypy  # noqa: E402
import validate_repository as validator  # noqa: E402

CANONICAL_SKILLS = {
    ("engineering", "audit-codebase"),
    ("engineering", "design-codebase"),
    ("engineering", "diagram-codebase"),
    ("engineering", "implement-plan"),
    ("engineering", "map-codebase"),
    ("engineering", "optimize-codebase"),
    ("engineering", "plan-change"),
    ("engineering", "scope-issue"),
    ("technical-communication", "manualize"),
}
CANONICAL_SKILL_NAMES = {name for _, name in CANONICAL_SKILLS}


def _skill_version(skill: Path) -> str:
    frontmatter = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    match = re.search(r"^version:\s*(.+)$", frontmatter, re.MULTILINE)
    assert match is not None
    return match.group(1).strip()


def test_repository_validation_passes() -> None:
    assert validator.main() == 0


def test_skill_discovery_matches_expected_directories() -> None:
    skills = validator.discover_skills()
    assert {(skill.parent.name, skill.name) for skill in skills} == CANONICAL_SKILLS


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

    for path in validator.tracked_files():
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


def test_package_and_independent_skill_versions_are_valid() -> None:
    assert validator.validate_version() == []
    assert validator.validate_version_description() == []
    assert all(not validator.validate_frontmatter(skill) for skill in validator.discover_skills())
    versions = {skill.name: _skill_version(skill) for skill in validator.discover_skills()}
    assert versions["map-codebase"] == "1.1.0"
    assert set(versions.values()) == {"1.0.0", "1.1.0"}
    assert validator.SEMVER_RE.fullmatch("1.0.0-alpha.1+build.7")
    assert not validator.SEMVER_RE.fullmatch("1.0.0-01")
    assert not validator.SEMVER_RE.fullmatch("1.0.0-alpha..1")


def test_release_description_is_required_and_nonempty(tmp_path: Path) -> None:
    description = tmp_path / "VERSION_DESC.md"
    assert validator.validate_version_description(description) == ["Missing VERSION_DESC.md"]

    description.write_text("\n", encoding="utf-8")
    assert validator.validate_version_description(description) == [
        "VERSION_DESC.md must contain the GitHub release summary"
    ]

    description.write_text("# Release summary\n\nUseful details.\n", encoding="utf-8")
    assert validator.validate_version_description(description) == []


def test_readme_latest_release_badge_tracks_package_version(tmp_path: Path) -> None:
    version = tmp_path / "VERSION"
    readme = tmp_path / "README.md"
    version.write_text("1.1.0\n", encoding="utf-8")
    badge = (
        "[![Latest Release]"
        "(https://img.shields.io/github/v/release/akshay-diwadkar/skills"
        "?sort=semver&display_name=tag&cacheSeconds=300&v=1.1.0)]"
        "(https://github.com/akshay-diwadkar/skills/releases/latest)\n"
    )
    readme.write_text(badge, encoding="utf-8")

    assert validator.validate_readme_release_link(readme, version) == []

    readme.write_text(badge.replace("v=1.1.0", "v=1.0.0"), encoding="utf-8")
    assert validator.validate_readme_release_link(readme, version) == [
        "README.md: Latest Release badge cache key must match VERSION "
        "(expected v=1.1.0)"
    ]

    readme.write_text(badge.replace("/releases/latest", "/releases/tag/v1.1.0"), encoding="utf-8")
    assert validator.validate_readme_release_link(readme, version) == [
        "README.md: Latest Release badge must target "
        "https://github.com/akshay-diwadkar/skills/releases/latest"
    ]


def test_marketplace_groups_every_skill_once() -> None:
    assert validator.validate_marketplace() == []
    expected_paths = set().union(*validator.EXPECTED_MARKETPLACE_GROUPS.values())
    assert expected_paths == {
        f"./skills/{domain}/{skill_name}" for domain, skill_name in CANONICAL_SKILLS
    }


def test_agent_instruction_versioning_policies_match() -> None:
    assert validator.validate_versioning_instructions() == []


def test_publish_release_workflow_uses_version_description() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    assert "paths:\n      - VERSION" in workflow
    assert "workflow_dispatch:" in workflow
    assert "contents: write" in workflow
    assert "VERSION_DESC.md must be updated in the same push as VERSION." in workflow
    assert "--notes-file VERSION_DESC.md" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "github.actor == github.repository_owner" in workflow
    assert "pull_request:" not in workflow


def test_pipeline_readmes_and_skill_changelog_are_supported_resources() -> None:
    engineering = REPO_ROOT / "skills" / "engineering"
    for skill_name in ("design-codebase", "plan-change", "scope-issue"):
        assert not validator.validate_skill_package(engineering / skill_name)
        assert (engineering / skill_name / "README.md").is_file()
    assert (engineering / "design-codebase" / "CHANGELOG.md").is_file()


def test_mypy_scopes_are_discovered_from_skill_directories() -> None:
    assert {name for name, _, _ in run_mypy.discover_skill_scopes()} == {
        f"{skill.parent.name}/{skill.name}" for skill in validator.discover_skills()
    }
