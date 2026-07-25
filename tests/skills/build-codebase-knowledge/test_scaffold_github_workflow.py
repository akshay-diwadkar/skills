import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from scaffold_github_workflow import BEGIN, scaffold_github_workflow

SHA = "a" * 40


def test_explicit_workflow_uses_requested_runtime_and_direct_commands(tmp_path: Path):
    result = scaffold_github_workflow(
        tmp_path,
        revision=SHA,
        repository="example/knowledge-runtime",
        runtime_dir=".runtime",
        branch="release",
    )
    content = Path(result["path"]).read_text(encoding="utf-8")
    assert result["status"] == "created"
    assert 'repository: "example/knowledge-runtime"' in content
    assert f'ref: "{SHA}"' in content
    assert 'python ".runtime/skills/engineering/build-codebase-knowledge/scripts/cli.py" status' in content
    assert 'python ".runtime/skills/engineering/build-codebase-knowledge/scripts/cli.py" refresh' in content
    assert "TOOL=" not in content


def test_workflow_protects_user_owned_file_unless_forced(tmp_path: Path):
    path = tmp_path / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    path.parent.mkdir(parents=True)
    path.write_text("name: User workflow\n", encoding="utf-8")
    warning = scaffold_github_workflow(tmp_path, revision=SHA)
    assert warning["status"] == "warning"
    assert path.read_text(encoding="utf-8") == "name: User workflow\n"
    forced = scaffold_github_workflow(tmp_path, revision=SHA, force=True)
    assert forced["status"] == "updated"
    assert BEGIN in path.read_text(encoding="utf-8")


def test_workflow_updates_managed_block_and_rejects_invalid_sha(tmp_path: Path):
    first = scaffold_github_workflow(tmp_path, revision=SHA)
    updated = scaffold_github_workflow(tmp_path, revision="b" * 40, branch="next")
    assert first["status"] == "created"
    assert updated["status"] == "updated"
    assert "next" in Path(updated["path"]).read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="revision"):
        scaffold_github_workflow(tmp_path, revision="not-a-sha")
