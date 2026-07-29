"""Release-focused coverage for the v5 knowledge lifecycle."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from refresh_knowledge import check_freshness, refresh_knowledge
from resolve_task import resolve_task
from scaffold_github_workflow import scaffold_github_workflow
from validate_knowledge import validate_knowledge


def test_role_aware_phase_one_owners(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def reset_password():\n    return True\n", encoding="utf-8")
    (tmp_path / "tests" / "test_auth.py").write_text("from src.auth import reset_password\ndef test_reset_password():\n    assert reset_password()\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    assert resolve_task(tmp_path, "Change Ruff line length in pyproject.toml", out)["targets"][0]["role"] == "configuration"
    assert resolve_task(tmp_path, "Fix the failing authentication test", out)["targets"][0]["role"] == "test"
    assert resolve_task(tmp_path, "Fix duplicate password-reset notifications", out)["targets"][0]["role"] == "source"


def test_untracked_safety_and_metadata_only_refresh(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.py").write_text("def tracked(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True, check=True)
    (tmp_path / "new.py").write_text("def untracked(): pass\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=supersecretvalue\n", encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"\0binary")
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    paths = {item["path"] for item in json.loads((out / "repo-map.json").read_text())["files"]}
    assert "new.py" in paths and ".env" not in paths and "data.bin" not in paths
    before = {name: (out / name).read_bytes() for name in ("repo-map.json", "symbols.json", "relationships.json")}
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "notes.py").write_text("ignored\n", encoding="utf-8")
    subprocess.run(["git", "add", "vendor/notes.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "irrelevant revision"], cwd=tmp_path, capture_output=True, check=True)
    status = check_freshness(tmp_path, out)
    assert status["status"] == "fresh" and status["revision_changed"] and status["changed_files"] == []
    assert refresh_knowledge(tmp_path, knowledge_dir=out)["mode"] == "metadata-only"
    assert before == {name: (out / name).read_bytes() for name in before}
    assert check_freshness(tmp_path, out)["status"] == "fresh"


def test_status_corruption_and_orphan_shards(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.py").write_text("def x(): pass\n", encoding="utf-8")
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    (out / "repo-map.json").write_text("{}", encoding="utf-8")
    assert check_freshness(tmp_path, out)["status"] == "invalid"
    build_knowledge(tmp_path, out)
    (out / "symbols" / "orphan.json").write_text("{}", encoding="utf-8")
    assert any("Orphan symbol shards" in error for error in validate_knowledge(tmp_path, out)["errors"])
    build_knowledge(tmp_path, out)
    assert not (out / "symbols" / "orphan.json").exists()


def test_workflow_paths_and_input_validation(tmp_path: Path):
    sha = "a" * 40
    prior = Path.cwd()
    os.chdir(tmp_path.parent)
    try:
        created = scaffold_github_workflow(tmp_path, revision=sha, workflow_file=".github/workflows/custom.yml")
    finally:
        os.chdir(prior)
    assert Path(created["path"]) == tmp_path / ".github" / "workflows" / "custom.yml"
    with pytest.raises(ValueError):
        scaffold_github_workflow(tmp_path, revision=sha, repository="https://example/repo")
    with pytest.raises(ValueError):
        scaffold_github_workflow(tmp_path, revision=sha, workflow_file=tmp_path.parent / "outside.yml")
