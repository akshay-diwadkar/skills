from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import run_mypy  # noqa: E402
import validate_repository as validator  # noqa: E402
import validate_skills_cli_install as install_validator  # noqa: E402

CANONICAL_SKILLS = {
    ("engineering", "audit-codebase"),
    ("engineering", "design-codebase"),
    ("engineering", "diagram-codebase"),
    ("engineering", "implement-plan"),
    ("engineering", "map-codebase"),
    ("engineering", "optimize-codebase"),
    ("engineering", "plan-change"),
    ("engineering", "raise-issue"),
    ("engineering", "route-engineering-work"),
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


def test_skill_packages_have_valid_invocation_metadata() -> None:
    assert validator.validate_invocation_policy() == []
    assert all((skill / "agents" / "openai.yaml").is_file() for skill in validator.discover_skills())
    assert validator.validate_retired_surfaces() == []


def test_certified_platforms_have_complete_installation_coverage() -> None:
    assert validator.validate_certified_platform_coverage() == []
    assert set(install_validator.INSTALL_ROOTS) == set(validator.CERTIFIED_PLATFORMS)
    assert install_validator.CLI_VERSION == validator.SKILLS_CLI_VERSION


def test_invocation_safety_capabilities_require_user_invocation() -> None:
    capabilities = {
        skill.name: validator.derive_invocation_safety_capabilities(skill)
        for skill in validator.discover_skills()
    }
    assert {name for name, values in capabilities.items() if values} == {
        "implement-plan",
        "raise-issue",
    }
    assert "external-write" in capabilities["raise-issue"]
    assert {"implementation", "repository-write"} <= capabilities["implement-plan"]


def test_invocation_registry_rejects_missing_stale_and_unknown_entries(tmp_path: Path) -> None:
    payload = json.loads(validator.INVOCATION_POLICY_PATH.read_text(encoding="utf-8"))
    payload["skills"].pop("map-codebase")
    payload["skills"]["retired-skill"] = "both"
    payload["skills"]["manualize"] = "sometimes"
    path = tmp_path / "invocation-policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    errors = validator.validate_invocation_policy(path)
    assert any("missing skills: ['map-codebase']" in error for error in errors)
    assert any("references unknown skills: ['retired-skill']" in error for error in errors)
    assert any("manualize has unsupported invocation mode 'sometimes'" in error for error in errors)


def test_invocation_validation_rejects_unsafe_implicit_policy(tmp_path: Path) -> None:
    source = REPO_ROOT / "skills" / "engineering" / "implement-plan"
    skill = tmp_path / "implement-plan"
    shutil.copytree(source, skill)

    errors = validator.validate_skill_invocation_metadata(skill, "both")
    assert any("authority-required capabilities" in error for error in errors)


def test_invocation_validation_rejects_malformed_openai_policy(tmp_path: Path) -> None:
    source = REPO_ROOT / "skills" / "engineering" / "map-codebase"
    skill = tmp_path / "map-codebase"
    shutil.copytree(source, skill)
    (skill / "agents" / "openai.yaml").write_text("policy: maybe\n", encoding="utf-8")

    errors = validator.validate_skill_invocation_metadata(skill, "model-invoked")
    assert any("unsupported or malformed policy" in error for error in errors)


def test_invocation_validation_rejects_frontmatter_adapter_mismatch(tmp_path: Path) -> None:
    source = REPO_ROOT / "skills" / "engineering" / "plan-change"
    skill = tmp_path / "plan-change"
    shutil.copytree(source, skill)
    skill_md = skill / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8").replace(
            "disable-model-invocation: false",
            "disable-model-invocation: true",
        ),
        encoding="utf-8",
    )

    errors = validator.validate_skill_invocation_metadata(skill, "both")
    assert any("disable-model-invocation must be false for both" in error for error in errors)


def test_package_and_independent_skill_versions_are_valid() -> None:
    assert validator.validate_version() == []
    assert validator.validate_version_description() == []
    assert all(not validator.validate_frontmatter(skill) for skill in validator.discover_skills())
    versions = {skill.name: _skill_version(skill) for skill in validator.discover_skills()}
    assert versions["map-codebase"] == "2.4.0"
    assert versions["audit-codebase"] == "4.1.0"
    assert versions["raise-issue"] == "1.0.0"
    assert versions["plan-change"] == "4.0.0"
    assert versions["design-codebase"] == "3.0.0"
    assert versions["implement-plan"] == "3.2.0"
    assert versions["scope-issue"] == "4.0.0"
    assert versions["optimize-codebase"] == "4.0.0"
    assert "3.0.0" in set(versions.values())
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


def test_readme_user_invoked_row_matches_invocation_policy() -> None:
    policy = json.loads((REPO_ROOT / "invocation-policy.json").read_text(encoding="utf-8"))
    expected = sorted(skill for skill, mode in policy["skills"].items() if mode == "user-invoked")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    row = next(line for line in readme.splitlines() if "| `user-invoked` |" in line)
    listed = [item.strip().strip("`") for item in row.split("|")[2].split(",")]
    assert sorted(listed) == expected


def test_marketplace_groups_every_skill_once() -> None:
    assert validator.validate_marketplace() == []
    expected_paths = set().union(*validator.EXPECTED_MARKETPLACE_GROUPS.values())
    assert expected_paths == {
        f"./skills/{domain}/{skill_name}" for domain, skill_name in CANONICAL_SKILLS
    }


def test_stateful_skill_protocol_manifests_are_valid() -> None:
    for skill_dir in validator.discover_skills():
        assert validator.validate_skill_protocol(skill_dir) == []


def test_router_contract_is_exact_and_read_only() -> None:
    assert validator.validate_router_contract() == []


def test_agent_instruction_versioning_policies_match() -> None:
    assert validator.validate_versioning_instructions() == []


def test_publish_release_workflow_uses_version_description() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    dependency_install = (
        "python -m pip install -r tools/validation/release-requirements.txt"
    )
    assert "paths:\n      - VERSION" in workflow
    assert "workflow_dispatch:" in workflow
    assert "contents: write" in workflow
    assert "actions/setup-python@v6" in workflow
    assert dependency_install in workflow
    assert workflow.index(dependency_install) < workflow.index(
        "python tools/validation/validate_repository.py"
    )
    assert "VERSION_DESC.md must be updated in the same push as VERSION." in workflow
    assert "--notes-file VERSION_DESC.md" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "github.actor == github.repository_owner" in workflow
    assert "pull_request:" not in workflow


def test_pre_release_workflow_matches_release_validation_environment() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pre-release.yml").read_text(
        encoding="utf-8"
    )
    requirements = (
        REPO_ROOT / "tools" / "validation" / "release-requirements.txt"
    ).read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "branches: [main]" in workflow
    assert "contents: read" in workflow
    assert "python -m pip install -r tools/validation/release-requirements.txt" in workflow
    assert "python tools/validation/validate_repository.py" in workflow
    for skill_requirements in (
        "structured-evidence-requirements.txt",
        "skills/engineering/map-codebase/requirements.txt",
        "skills/engineering/scope-issue/requirements.txt",
        "skills/technical-communication/manualize/requirements.txt",
    ):
        assert skill_requirements in requirements


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
