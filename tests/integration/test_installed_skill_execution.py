from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def installed_skills_env(tmp_path: Path):
    """Copy skills to an isolated external location and setup a separate target workspace with spaces."""
    installed_dir = tmp_path / "installed skills folder"
    target_repo = tmp_path / "target user project with spaces"
    installed_dir.mkdir(parents=True, exist_ok=True)
    target_repo.mkdir(parents=True, exist_ok=True)

    # Initialize a minimal git repository in target_repo
    subprocess.run(["git", "init"], cwd=target_repo, capture_output=True, check=True)
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
    scaffold_script = plan_skill / "scripts" / "scaffold_plan.py"
    finalize_script = plan_skill / "scripts" / "finalize_plan.py"

    assert scaffold_script.is_file()
    assert finalize_script.is_file()

    # 1. Run scaffold_plan from target_repo CWD
    scaffold_res = subprocess.run(
        [sys.executable, str(scaffold_script), "--tier", "tiny", "--task-type", "bug-fix"],
        cwd=target_repo,
        capture_output=True,
        text=True,
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

    # 2. Run finalize_plan from target_repo CWD
    finalize_res = subprocess.run(
        [
            sys.executable,
            str(finalize_script),
            "--tier",
            "tiny",
            "--repo-root",
            str(target_repo),
            str(draft_file),
        ],
        cwd=target_repo,
        capture_output=True,
        text=True,
    )
    assert finalize_res.returncode == 0, f"Finalizer stderr: {finalize_res.stderr}"
    assert "plan-validation: 3" in finalize_res.stdout


def test_installed_codebase_issue_auditor_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    auditor_skill = installed_dir / "codebase-issue-auditor"
    validate_script = auditor_skill / "scripts" / "validate_audit_bundle.py"

    valid_bundle_fixture = REPO_ROOT / "tests" / "skills" / "codebase-issue-auditor" / "fixtures" / "valid_bundle.json"
    bundle_data = json.loads(valid_bundle_fixture.read_text(encoding="utf-8"))

    bundle_file = target_repo / "audit-bundle.json"
    bundle_file.write_text(json.dumps(bundle_data), encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(validate_script), str(bundle_file)],
        cwd=target_repo,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Validator stderr: {res.stderr}"


def test_installed_create_diagram_execution(installed_skills_env):
    installed_dir, target_repo = installed_skills_env
    diagram_skill = installed_dir / "create-diagram"
    build_script = diagram_skill / "scripts" / "build_diagram.py"
    validate_script = diagram_skill / "scripts" / "validate_diagram.py"

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

    # Build diagram
    build_res = subprocess.run(
        [
            sys.executable,
            str(build_script),
            "--data",
            str(payload_file),
            "--output",
            str(output_file),
            "--overwrite",
        ],
        cwd=target_repo,
        capture_output=True,
        text=True,
    )
    assert build_res.returncode == 0, f"Build stderr: {build_res.stderr}"

    # Validate diagram
    val_res = subprocess.run(
        [sys.executable, str(validate_script), str(output_file)],
        cwd=target_repo,
        capture_output=True,
        text=True,
    )
    assert val_res.returncode == 0, f"Validate stderr: {val_res.stderr}"
