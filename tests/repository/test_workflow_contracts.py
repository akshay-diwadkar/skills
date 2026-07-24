"""Tests to verify release workflow safety and workflow contract invariants."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def test_single_release_workflow_exists() -> None:
    release_files = list(WORKFLOWS_DIR.glob("*release*.yml")) + list(WORKFLOWS_DIR.glob("*release*.yaml"))
    assert len(release_files) == 1, f"Expected exactly 1 release workflow file, found: {release_files}"
    assert release_files[0].name == "release.yml"


def test_release_workflow_gates_and_dependencies() -> None:
    release_file = WORKFLOWS_DIR / "release.yml"
    assert release_file.is_file()

    text = release_file.read_text(encoding="utf-8")
    content = yaml.safe_load(text)

    jobs = content.get("jobs", {})
    assert "validate-release-gates" in jobs
    assert "publish-release" in jobs

    publish_job = jobs["publish-release"]
    needs = publish_job.get("needs")
    assert needs == "validate-release-gates" or needs == ["validate-release-gates"]

    # Verify mandatory gate commands are present in validate-release-gates step runs
    steps = jobs["validate-release-gates"].get("steps", [])
    commands = " ".join(step.get("run", "") for step in steps)

    mandatory_snippets = [
        "ruff check .",
        "tools/validation/run_mypy.py",
        "tools/release/check_version.py",
        "tools/release/build_changelog.py",
        "tools/catalog/validate_catalog.py",
        "tools/catalog/sync_catalog.py --check",
        "tools/validation/validate_repository.py",
        "tools/validation/validate_links.py",
        "tools/validation/validate_dependencies.py",
        "tools/packaging/verify_distribution.py",
        "pytest",
    ]

    for snippet in mandatory_snippets:
        assert snippet in commands, f"Mandatory release gate missing: '{snippet}'"


def test_no_workflow_pushes_git_tags_on_dispatch() -> None:
    for wf in WORKFLOWS_DIR.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        if "workflow_dispatch" in text:
            # Ensure workflow dispatch does not git push origin tags which re-trigger push: tags
            assert "git push origin \"$TAG\"" not in text
            assert "git push origin ${TAG}" not in text
