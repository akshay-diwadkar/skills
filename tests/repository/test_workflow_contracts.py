"""Tests to verify release workflow safety and workflow contract invariants."""

from __future__ import annotations

import subprocess
import sys
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


def test_release_workflow_permissions_and_tag_validation() -> None:
    release_file = WORKFLOWS_DIR / "release.yml"
    assert release_file.is_file()

    text = release_file.read_text(encoding="utf-8")
    content = yaml.safe_load(text)

    # Top-level permissions must be read-only
    top_perms = content.get("permissions", {})
    assert top_perms.get("contents") != "write", "Top-level release workflow permissions must not grant contents: write"

    jobs = content.get("jobs", {})
    validate_job = jobs.get("validate-release-gates", {})
    val_perms = validate_job.get("permissions", {})
    assert val_perms.get("contents") != "write", "validate-release-gates job must have read-only permissions"

    publish_job = jobs.get("publish-release", {})
    pub_perms = publish_job.get("permissions", {})
    assert pub_perms.get("contents") == "write", "publish-release job must have scoped contents: write permission"

    # Verify tag validation step exists
    steps = validate_job.get("steps", [])
    commands = " ".join(step.get("run", "") for step in steps)
    assert "tools/release/check_version.py --tag" in commands, "validate-release-gates must run check_version.py --tag"
    assert "GITHUB_SHA" in text, "release workflow must reference GITHUB_SHA for commit binding"
    assert "target_commitish: ${{ github.sha }}" in text, "publish-release action must set target_commitish to github.sha"


def test_check_version_tag_mismatch_rejection() -> None:
    check_version_script = REPO_ROOT / "tools" / "release" / "check_version.py"
    res = subprocess.run([sys.executable, str(check_version_script), "--tag", "v9.9.9"], capture_output=True, text=True)
    assert res.returncode != 0
    assert "does not match expected tag" in res.stderr or "does not match expected tag" in res.stdout


def test_command_path_contract_validation() -> None:
    """Verify command path contract validator rejects relative non-script filesystem arguments and passes on absolute examples."""
    sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))
    import validate_repository

    # 1. Real repository check must pass cleanly
    repo_errors = validate_repository.validate_command_path_contracts()
    assert not repo_errors, "Repository command path validation failed:\n" + "\n".join(repo_errors)

    # 2. Test rejection of relative filesystem flag examples
    invalid_examples = [
        "python scripts/post_merge_issue_followup.py --env .env --github-repo-url owner/repo",
        "python scripts/build_diagram.py --output diagram.html",
        "python scripts/build_diagram.py --data payload.json",
        "python scripts/check_issue_plan.py issue-plan.md --repo-root <checkout>",
        "python scripts/check_issue_plan.py <run-dir>/issue-1.md --repo-root /absolute/path/to/repo",
        "python scripts/check_issue_plan.py /absolute/path/to/plan.md --issue-json fresh-issue.json",
        "python scripts/post_merge_issue_followup.py --verification-summary-file summary.md",
    ]

    for ex in invalid_examples:
        cmd_tokens = ex.split()
        has_invalid = False
        for i, tok in enumerate(cmd_tokens):
            if tok in validate_repository.FILESYSTEM_FLAGS:
                if i + 1 < len(cmd_tokens) and not validate_repository.is_visibly_absolute(cmd_tokens[i + 1]):
                    has_invalid = True
            elif i > 0 and cmd_tokens[i - 1] not in validate_repository.FILESYSTEM_FLAGS and not tok.startswith("-"):
                if (
                    tok.startswith(("<run-dir>", "<issue-plan", "<fresh-issue"))
                    or (any(tok.endswith(ext) for ext in (".md", ".json", ".html", ".py")) and not tok.startswith("scripts/"))
                ):
                    if not validate_repository.is_visibly_absolute(tok):
                        has_invalid = True
        assert has_invalid, f"Expected validation failure for invalid command example: '{ex}'"

    # 3. Test allowance of valid absolute examples and non-filesystem arguments
    valid_examples = [
        "python scripts/post_merge_issue_followup.py --env /absolute/path/to/repository/.env --github-repo-url owner/repo --base main --issue-number <number>",
        "python scripts/build_diagram.py --output /absolute/path/to/diagram.html",
        "python scripts/check_issue_plan.py /absolute/path/to/run-dir/issue-1.md --repo-root /absolute/path/to/repository",
    ]

    for ex in valid_examples:
        cmd_tokens = ex.split()
        for i, tok in enumerate(cmd_tokens):
            if tok in validate_repository.FILESYSTEM_FLAGS:
                val = cmd_tokens[i + 1]
                assert validate_repository.is_visibly_absolute(val), f"Expected visibly absolute path for option '{tok}', got: {val}"

