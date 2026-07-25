import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from scaffold_github_workflow import BEGIN, END, LEGACY_BEGIN, LEGACY_END, scaffold_github_workflow

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
    assert BEGIN == "# BEGIN MAP-CODEBASE WORKFLOW"
    assert END == "# END MAP-CODEBASE WORKFLOW"
    assert content.count(BEGIN) == 1
    assert content.count(END) == 1
    assert LEGACY_BEGIN not in content
    assert LEGACY_END not in content
    assert 'repository: "example/knowledge-runtime"' in content
    assert f'ref: "{SHA}"' in content
    assert 'python ".runtime/skills/engineering/map-codebase/scripts/cli.py" status' in content
    assert 'python ".runtime/skills/engineering/map-codebase/scripts/cli.py" refresh' in content
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
    forced_content = path.read_text(encoding="utf-8")
    assert BEGIN in forced_content
    assert LEGACY_BEGIN not in forced_content


def test_workflow_updates_managed_block_and_rejects_invalid_sha(tmp_path: Path):
    first = scaffold_github_workflow(tmp_path, revision=SHA)
    updated = scaffold_github_workflow(tmp_path, revision="b" * 40, branch="next")
    assert first["status"] == "created"
    assert updated["status"] == "updated"
    assert "next" in Path(updated["path"]).read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="revision"):
        scaffold_github_workflow(tmp_path, revision="not-a-sha")


def test_legacy_managed_workflow_migrates_in_place_and_is_idempotent(tmp_path: Path):
    path = tmp_path / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"name: Existing wrapper\n\n{LEGACY_BEGIN}\nold managed content\n{LEGACY_END}\n\n# unrelated footer\n",
        encoding="utf-8",
    )

    updated = scaffold_github_workflow(tmp_path, revision=SHA)
    content = path.read_text(encoding="utf-8")
    assert updated["status"] == "updated"
    assert content.count(BEGIN) == 1
    assert content.count(END) == 1
    assert LEGACY_BEGIN not in content
    assert LEGACY_END not in content
    assert "old managed content" not in content
    assert "name: Existing wrapper" in content
    assert "# unrelated footer" in content

    unchanged = scaffold_github_workflow(tmp_path, revision=SHA)
    assert unchanged["status"] == "unchanged"
    assert path.read_text(encoding="utf-8") == content


def test_canonical_managed_workflow_is_idempotent(tmp_path: Path):
    created = scaffold_github_workflow(tmp_path, revision=SHA)
    content = Path(created["path"]).read_text(encoding="utf-8")

    unchanged = scaffold_github_workflow(tmp_path, revision=SHA)
    assert unchanged["status"] == "unchanged"
    assert Path(created["path"]).read_text(encoding="utf-8") == content
    assert content.count(BEGIN) == 1
    assert content.count(END) == 1


@pytest.mark.parametrize(
    "content",
    [
        f"{BEGIN}\n",
        f"{BEGIN}\nbody\n{LEGACY_END}\n",
        f"{BEGIN}\nbody\n{END}\n\n{LEGACY_BEGIN}\nbody\n{LEGACY_END}\n",
    ],
)
def test_malformed_managed_workflow_is_rejected_without_writing(tmp_path: Path, content: str):
    path = tmp_path / ".github" / "workflows" / "refresh-codebase-knowledge.yml"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed managed workflow"):
        scaffold_github_workflow(tmp_path, revision=SHA)
    assert path.read_text(encoding="utf-8") == content
