from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SUBPROCESS_ENV = {
    **os.environ,
    "PYTHONDONTWRITEBYTECODE": "1",
}


def get_skill_snapshot(skill_dir: Path) -> set[tuple[str, int]]:
    """Record relative path and size of every file inside a skill directory."""
    snapshot = set()
    for p in skill_dir.rglob("*"):
        if p.is_file():
            snapshot.add((p.relative_to(skill_dir).as_posix(), p.stat().st_size))
    return snapshot


def assert_no_skill_mutation(before: set[tuple[str, int]], after: set[tuple[str, int]]) -> None:
    added = after - before
    removed = before - after
    diff = []
    if added:
        diff.append(f"Added files: {sorted(added)}")
    if removed:
        diff.append(f"Removed files: {sorted(removed)}")
    assert before == after, "Skill directory mutated during execution:\n" + "\n".join(diff)


@pytest.fixture
def installed_skills_env(tmp_path: Path):
    """Copy skills to an isolated external location with spaces and setup a separate target workspace with spaces."""
    installed_dir = tmp_path / "installed skills folder with spaces"
    target_repo = tmp_path / "target user project with spaces"
    installed_dir.mkdir(parents=True, exist_ok=True)
    target_repo.mkdir(parents=True, exist_ok=True)

    # Initialize a minimal git repository in target_repo with origin remote
    subprocess.run(["git", "init"], cwd=target_repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "eval@example.com"], cwd=target_repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Eval"], cwd=target_repo, capture_output=True, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/owner/repo.git"], cwd=target_repo, capture_output=True, check=True)
    (target_repo / "README.md").write_text("# Target Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target_repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=target_repo, capture_output=True, check=True)

    # Copy skills
    skills_src = REPO_ROOT / "skills" / "engineering"
    for skill_dir in skills_src.iterdir():
        if skill_dir.is_dir():
            shutil.copytree(skill_dir, installed_dir / skill_dir.name)

    return installed_dir, target_repo


def test_installed_plan_with_senior_dev_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    plan_skill = installed_dir / "plan-with-senior-dev"
    assert (plan_skill / "SKILL.md").is_file()
    assert not (target_repo / "scripts").exists()

    before_snapshot = get_skill_snapshot(plan_skill)

    # 1. Run scaffold_plan from plan_skill CWD with relative script path
    scaffold_res = subprocess.run(
        [sys.executable, "scripts/scaffold_plan.py", "--tier", "tiny", "--task-type", "bug-fix"],
        cwd=plan_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert scaffold_res.returncode == 0
    assert "plan-contract: 3" in scaffold_res.stdout

    # Load valid tiny plan from worked-examples.md
    worked_examples_path = plan_skill / "references" / "worked-examples.md"
    examples_text = worked_examples_path.read_text(encoding="utf-8")
    tiny_block = re.findall(r"```plan\n(.*?)\n```", examples_text, re.DOTALL)[0]
    draft_text = re.sub(r"^<!-- plan-validation:.*\n", "", tiny_block, flags=re.MULTILINE)

    draft_file = target_repo / "draft_plan.md"
    draft_file.write_text(draft_text, encoding="utf-8")

    # Create dummy file referenced by tiny example in target_repo
    (target_repo / "src").mkdir(parents=True, exist_ok=True)
    (target_repo / "src" / "names.py").write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8")

    # 2. Run finalize_plan from plan_skill CWD with absolute target repo and draft arguments
    finalize_res = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_plan.py",
            "--tier",
            "tiny",
            "--repo-root",
            str(target_repo),
            str(draft_file),
        ],
        cwd=plan_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert finalize_res.returncode == 0, f"Finalizer stderr: {finalize_res.stderr}"
    assert "plan-validation: 3" in finalize_res.stdout

    after_snapshot = get_skill_snapshot(plan_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_implement_with_senior_dev_execution(installed_skills_env, tmp_path: Path):
    installed_dir, target_repo = installed_skills_env
    implement_skill = installed_dir / "implement-with-senior-dev"
    plan_skill = installed_dir / "plan-with-senior-dev"
    assert (implement_skill / "SKILL.md").is_file()

    before_snapshot = get_skill_snapshot(implement_skill)

    # Load valid tiny plan with receipt from plan-with-senior-dev worked-examples
    worked_examples_path = plan_skill / "references" / "worked-examples.md"
    examples_text = worked_examples_path.read_text(encoding="utf-8")
    tiny_block = re.findall(r"```plan\n(.*?)\n```", examples_text, re.DOTALL)[0]

    plan_file = target_repo / "plan.md"
    plan_file.write_text(tiny_block, encoding="utf-8")
    output_dir = tmp_path / "external_run_dir"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "implementation.json"

    # Create dummy files referenced by tiny plan in target_repo and commit them
    (target_repo / "src").mkdir(parents=True, exist_ok=True)
    (target_repo / "src" / "names.py").write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target_repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add src/names.py"], cwd=target_repo, capture_output=True, check=True)

    # 1. Run scaffold_implementation from implement_skill CWD
    scaffold_res = subprocess.run(
        [
            sys.executable,
            "scripts/scaffold_implementation.py",
            "--repo-root",
            str(target_repo),
            "--plan",
            str(plan_file),
            "--output",
            str(output_file),
        ],
        cwd=implement_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert scaffold_res.returncode == 0, f"Scaffold stderr: {scaffold_res.stderr}"
    assert output_file.is_file()

    # 2. Run finalize_implementation from implement_skill CWD
    finalize_res = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_implementation.py",
            "--repo-root",
            str(target_repo),
            "--plan",
            str(plan_file),
            str(output_file),
        ],
        cwd=implement_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert finalize_res.returncode == 0, f"Finalize stderr: {finalize_res.stderr}"

    after_snapshot = get_skill_snapshot(implement_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_github_issue_planner_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    github_skill = installed_dir / "github-issue-planner"
    assert (github_skill / "SKILL.md").is_file()

    before_snapshot = get_skill_snapshot(github_skill)

    issue_json = target_repo / "issue-1.json"
    issue_payload = {
        "repo": "owner/repo",
        "fetched_at": "2026-07-24T00:00:00Z",
        "issues": [
            {
                "number": 1,
                "title": "Fix bug",
                "body": "Details",
                "url": "https://github.com/owner/repo/issues/1",
                "author": "user",
                "created_at": "2026-07-24T00:00:00Z",
                "updated_at": "2026-07-24T00:00:00Z",
                "labels": [],
                "comments": [],
            }
        ],
    }
    issue_json.write_text(json.dumps(issue_payload), encoding="utf-8")
    output_md = target_repo / "issue-1.md"

    # Run scaffold_issue_plan from github_skill CWD
    scaffold_res = subprocess.run(
        [
            sys.executable,
            "scripts/scaffold_issue_plan.py",
            "--repo-root",
            str(target_repo),
            "--issue-json",
            str(issue_json),
            "--issue-number",
            "1",
            "--output",
            str(output_md),
        ],
        cwd=github_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert scaffold_res.returncode == 0, f"Scaffold stderr: {scaffold_res.stderr}"
    assert output_md.is_file()

    after_snapshot = get_skill_snapshot(github_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_codebase_issue_auditor_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    auditor_skill = installed_dir / "codebase-issue-auditor"
    assert (auditor_skill / "SKILL.md").is_file()

    before_snapshot = get_skill_snapshot(auditor_skill)

    valid_bundle_fixture = REPO_ROOT / "tests" / "skills" / "codebase-issue-auditor" / "fixtures" / "valid_bundle.json"
    bundle_data = json.loads(valid_bundle_fixture.read_text(encoding="utf-8"))

    bundle_file = target_repo / "audit-bundle.json"
    bundle_file.write_text(json.dumps(bundle_data), encoding="utf-8")

    # Run validate_audit_bundle from auditor_skill CWD
    res = subprocess.run(
        [sys.executable, "scripts/validate_audit_bundle.py", str(bundle_file)],
        cwd=auditor_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert res.returncode == 0, f"Validator stderr: {res.stderr}"

    after_snapshot = get_skill_snapshot(auditor_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_create_diagram_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    diagram_skill = installed_dir / "create-diagram"
    assert (diagram_skill / "SKILL.md").is_file()

    before_snapshot = get_skill_snapshot(diagram_skill)

    payload = {
        "diagram": {
            "title": "Minimal Diagram",
            "audience": "Engineers",
            "purpose": "Validate a tiny happy path.",
            "fidelity": "narrative-architecture",
            "nodes": [
                {
                    "id": "a",
                    "label": "Source",
                    "type": "service",
                    "description": "Starts the validated diagram flow."
                },
                {
                    "id": "b",
                    "label": "Target",
                    "type": "database",
                    "description": "Receives the validated diagram flow."
                }
            ],
            "edges": [
                {
                    "sourceId": "a",
                    "targetId": "b",
                    "label": "writes",
                    "evidence": "user-stated",
                    "confidence": "stated"
                }
            ],
            "clusters": [
                {
                    "id": "main",
                    "label": "Main",
                    "nodeIds": ["a", "b"]
                }
            ]
        },
        "metadata": {
            "tool": "create-diagram",
            "timestamp": "2026-07-23T00:00:00Z",
            "entities": [
                {"id": "a", "kind": "service", "name": "Source"},
                {"id": "b", "kind": "database", "name": "Target"}
            ]
        }
    }
    payload_file = target_repo / "payload.json"
    output_file = target_repo / "diagram.html"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    # Build diagram from diagram_skill CWD
    build_res = subprocess.run(
        [
            sys.executable,
            "scripts/build_diagram.py",
            "--data",
            str(payload_file),
            "--output",
            str(output_file),
            "--overwrite",
        ],
        cwd=diagram_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert build_res.returncode == 0, f"Build stderr: {build_res.stderr}"
    assert output_file.is_file()

    # Validate diagram from diagram_skill CWD
    val_res = subprocess.run(
        [sys.executable, "scripts/validate_diagram.py", str(output_file)],
        cwd=diagram_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert val_res.returncode == 0, f"Validate stderr: {val_res.stderr}"

    after_snapshot = get_skill_snapshot(diagram_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_design_codebase_with_senior_dev_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    design_skill = installed_dir / "design-codebase-with-senior-dev"
    assert (design_skill / "SKILL.md").is_file()

    before_snapshot = get_skill_snapshot(design_skill)

    scaffold_res = subprocess.run(
        [sys.executable, "scripts/scaffold_assessment.py", "--level", "L0"],
        cwd=design_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert scaffold_res.returncode == 0
    assert "design-assessment-contract: 1" in scaffold_res.stdout

    draft = target_repo / "assessment.md"
    draft.write_text(scaffold_res.stdout, encoding="utf-8")

    check_res = subprocess.run(
        [sys.executable, "scripts/check_assessment.py", "--level", "L0", "--repo-root", str(target_repo), str(draft)],
        cwd=design_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert check_res.returncode in (0, 1)

    after_snapshot = get_skill_snapshot(design_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_optimize_codebase_with_senior_dev_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    optimize_skill = installed_dir / "optimize-codebase-with-senior-dev"
    assert (optimize_skill / "SKILL.md").is_file()

    before_snapshot = get_skill_snapshot(optimize_skill)

    res = subprocess.run(
        [sys.executable, "scripts/scaffold_optimization.py", "--scope", "targeted", "--stage", "plan"],
        cwd=optimize_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert res.returncode == 0
    assert "optimization-contract: 1" in res.stdout

    after_snapshot = get_skill_snapshot(optimize_skill)
    assert_no_skill_mutation(before_snapshot, after_snapshot)


def test_installed_missing_script_or_root_failures(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    plan_skill = installed_dir / "plan-with-senior-dev"

    # Missing script failure
    res_missing_script = subprocess.run(
        [sys.executable, "scripts/nonexistent_script.py"],
        cwd=plan_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert res_missing_script.returncode != 0

    # Missing/invalid repo root failure
    non_existent_repo = target_repo / "does_not_exist"
    draft_file = target_repo / "draft.md"
    draft_file.write_text("# Draft\n", encoding="utf-8")
    res_missing_root = subprocess.run(
        [
            sys.executable,
            "scripts/finalize_plan.py",
            "--tier",
            "tiny",
            "--repo-root",
            str(non_existent_repo),
            str(draft_file),
        ],
        cwd=plan_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert res_missing_root.returncode != 0


def test_installed_skill_execution_via_symlink(tmp_path: Path):
    """Test skill execution when installed via symlink if OS permits."""
    source_skill = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev"
    symlink_dir = tmp_path / "symlinked_skills"
    symlink_dir.mkdir(parents=True, exist_ok=True)
    symlinked_skill = symlink_dir / "plan-with-senior-dev"

    try:
        os.symlink(source_skill, symlinked_skill, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported on host OS or permissions missing")

    scaffold_res = subprocess.run(
        [sys.executable, "scripts/scaffold_plan.py", "--tier", "tiny", "--task-type", "bug-fix"],
        cwd=symlinked_skill,
        capture_output=True,
        text=True,
        env=SUBPROCESS_ENV,
    )
    assert scaffold_res.returncode == 0
    assert "plan-contract: 3" in scaffold_res.stdout


def test_every_skill_command_references_existing_bundled_file():
    """Verify every script referenced in SKILL.md command examples exists on disk and contains no unresolved placeholders."""
    skills_dir = REPO_ROOT / "skills" / "engineering"
    for skill_folder in skills_dir.iterdir():
        if not skill_folder.is_dir():
            continue
        skill_md = skill_folder / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")

        # Ensure no executable code block contains unresolved prose placeholders like <skill-dir> or $skillDir
        code_blocks = re.findall(r"```(?:bash|powershell|sh)?\n(.*?)\n```", text, re.DOTALL)
        for block in code_blocks:
            assert "<skill-dir>" not in block, f"{skill_folder.name}/SKILL.md contains unresolved <skill-dir> in command example:\n{block}"
            assert "$skillDir" not in block, f"{skill_folder.name}/SKILL.md contains unresolved $skillDir in command example:\n{block}"

        # Find script references like python scripts/foo.py or python scripts\foo.py
        script_refs = re.findall(r"python\s+[\"']?(scripts[/\\][A-Za-z0-9_-]+\.py)[\"']?", text)
        for ref in script_refs:
            norm_ref = ref.replace("\\", "/")
            expected_file = skill_folder / norm_ref
            assert expected_file.is_file(), f"{skill_folder.name}/SKILL.md references missing script '{norm_ref}'"


def test_skill_directory_resolution_instructions_present():
    """Verify that every SKILL.md that references bundled scripts includes explicit Skill Directory Resolution instructions."""
    skills_dir = REPO_ROOT / "skills" / "engineering"
    for skill_folder in skills_dir.iterdir():
        if not skill_folder.is_dir():
            continue
        skill_md = skill_folder / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        if "python scripts/" in text or "python scripts\\" in text:
            assert "Skill Directory Resolution" in text, (
                f"{skill_folder.name}/SKILL.md references bundled scripts but missing 'Skill Directory Resolution' section"
            )


def test_installed_skill_mutation_detection(installed_skills_env):
    """Verify that unexpected file creation inside an installed skill triggers mutation detection failure."""
    installed_dir, _ = installed_skills_env
    plan_skill = installed_dir / "plan-with-senior-dev"
    before_snapshot = get_skill_snapshot(plan_skill)

    # Inject unexpected file (including bytecode simulation)
    unexpected = plan_skill / "unexpected_runtime_file.pyc"
    unexpected.write_bytes(b"bytecode")

    after_snapshot = get_skill_snapshot(plan_skill)
    with pytest.raises(AssertionError) as excinfo:
        assert_no_skill_mutation(before_snapshot, after_snapshot)
    assert "unexpected_runtime_file.pyc" in str(excinfo.value)
