import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from scaffold_github_workflow import scaffold_github_workflow


def test_scaffold_github_workflow_default(tmp_path: Path):
    res = scaffold_github_workflow(tmp_path)
    assert res["status"] == "success"
    assert res["branch"] == "main"

    wf_file = tmp_path / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    assert wf_file.is_file()

    content = wf_file.read_text(encoding="utf-8")
    assert "branches:\n      - main" in content
    assert "paths-ignore:\n      - '.agent/knowledge/**'" in content
    assert "commit_message: \"docs(knowledge): auto-refresh codebase knowledge [skip ci]\"" in content


def test_scaffold_github_workflow_custom_branch(tmp_path: Path):
    res = scaffold_github_workflow(tmp_path, branch="release/v1.0")
    assert res["status"] == "success"
    assert res["branch"] == "release/v1.0"

    wf_file = tmp_path / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    content = wf_file.read_text(encoding="utf-8")
    assert "branches:\n      - release/v1.0" in content


def test_scaffold_github_workflow_overwrite_protection(tmp_path: Path):
    res1 = scaffold_github_workflow(tmp_path)
    assert res1["status"] == "success"

    # Second call without force should fail
    res2 = scaffold_github_workflow(tmp_path)
    assert res2["status"] == "error"
    assert "already exists" in res2["message"]

    # Call with force=True should succeed
    res3 = scaffold_github_workflow(tmp_path, force=True)
    assert res3["status"] == "success"


def test_scaffold_github_workflow_custom_output(tmp_path: Path):
    custom_output = tmp_path / "custom-ci.yml"
    res = scaffold_github_workflow(tmp_path, workflow_file=custom_output)
    assert res["status"] == "success"
    assert custom_output.is_file()
