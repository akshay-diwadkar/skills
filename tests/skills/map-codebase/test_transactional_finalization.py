"""Regression coverage for shared finalization and agent-document transactions."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import link_agent_docs

AgentDocumentError = link_agent_docs.AgentDocumentError
MANAGED_BEGIN = link_agent_docs.MANAGED_BEGIN
ensure_agent_docs = link_agent_docs.ensure_agent_docs


def _run(script: str, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / script), "--repo-root", str(repo_root), *args],
        capture_output=True,
        text=True,
    )


def _assert_docs(repo_root: Path, knowledge_path: str = ".agent/knowledge/") -> None:
    for name in ("AGENTS.md", "CLAUDE.md"):
        content = (repo_root / name).read_text(encoding="utf-8")
        assert content.count("## Repository Knowledge") == 1
        assert f"Read `{knowledge_path}KNOWLEDGE.md` before repository exploration." in content
        assert MANAGED_BEGIN not in content
    assert (repo_root / knowledge_path / "KNOWLEDGE.md").is_file()


def test_standalone_build_finalizes_docs_and_custom_output(sample_repo: Path):
    result = _run("build_knowledge.py", sample_repo, "--output", ".cache/custom-map", "--format", "json")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["agent_docs"]["status"] == "success"
    assert (sample_repo / ".cache" / "custom-map" / "manifest.json").is_file()
    _assert_docs(sample_repo, ".cache/custom-map/")


def test_standalone_refresh_finalizes_incremental_and_metadata_only(sample_repo: Path):
    assert _run("build_knowledge.py", sample_repo).returncode == 0
    (sample_repo / "CLAUDE.md").unlink()
    service = sample_repo / "src" / "auth" / "service.py"
    service.write_text(service.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    incremental = _run("refresh_knowledge.py", sample_repo, "--changed-file", str(service), "--format", "json")
    assert incremental.returncode == 0, incremental.stderr
    assert json.loads(incremental.stdout)["status"] == "fresh"
    _assert_docs(sample_repo)

    subprocess.run(["git", "commit", "--allow-empty", "-m", "metadata only"], cwd=sample_repo, check=True)
    (sample_repo / "CLAUDE.md").unlink()
    metadata = _run("refresh_knowledge.py", sample_repo, "--format", "json")
    assert metadata.returncode == 0, metadata.stderr
    assert json.loads(metadata.stdout)["mode"] == "metadata-only"
    _assert_docs(sample_repo)


def test_unified_and_standalone_build_have_equivalent_finalization(sample_repo: Path, tmp_path: Path):
    standalone = sample_repo
    unified = tmp_path / "unified"
    subprocess.run(["git", "clone", str(standalone), str(unified)], check=True, capture_output=True)

    first = _run("build_knowledge.py", standalone, "--output", ".cache/map", "--format", "json")
    second = subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "cli.py"), "build", "--repo-root", str(unified), "--output", ".cache/map", "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout)["status"] == json.loads(second.stdout)["status"] == "success"
    _assert_docs(standalone, ".cache/map/")
    _assert_docs(unified, ".cache/map/")


def test_unified_and_standalone_refresh_have_equivalent_finalization(sample_repo: Path, tmp_path: Path):
    standalone = sample_repo
    unified = tmp_path / "unified"
    subprocess.run(["git", "clone", str(standalone), str(unified)], check=True, capture_output=True)
    assert _run("build_knowledge.py", standalone, "--format", "json").returncode == 0
    assert subprocess.run(
        [sys.executable, str(SKILL_SCRIPTS / "cli.py"), "build", "--repo-root", str(unified), "--format", "json"],
        capture_output=True,
        text=True,
    ).returncode == 0
    for repo in (standalone, unified):
        service = repo / "src" / "auth" / "service.py"
        service.write_text(service.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
        (repo / "CLAUDE.md").unlink()

    first = _run("refresh_knowledge.py", standalone, "--changed-file", "src/auth/service.py", "--format", "json")
    second = subprocess.run(
        [
            sys.executable,
            str(SKILL_SCRIPTS / "cli.py"),
            "refresh",
            "--repo-root",
            str(unified),
            "--changed-file",
            "src/auth/service.py",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    assert first.returncode == second.returncode == 0
    assert json.loads(first.stdout)["mode"] == json.loads(second.stdout)["mode"]
    _assert_docs(standalone)
    _assert_docs(unified)


def test_second_write_failure_restores_existing_files_and_cleans_temps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paths = [tmp_path / name for name in ("AGENTS.md", "CLAUDE.md")]
    for path in paths:
        path.write_bytes(f"# {path.name}\n".encode())
    before = {path: path.read_bytes() for path in paths}
    original = link_agent_docs._atomic_replace

    def fail_claude(path: Path, content: bytes, mode: int | None = None) -> None:
        if path.name == "CLAUDE.md" and content != before[path]:
            raise OSError("second replacement failed")
        original(path, content, mode)

    monkeypatch.setattr(link_agent_docs, "_atomic_replace", fail_claude)
    with pytest.raises(AgentDocumentError, match="failed to commit agent documents"):
        ensure_agent_docs(tmp_path)
    assert before == {path: path.read_bytes() for path in paths}
    assert not list(tmp_path.glob(".*.map-codebase-*.tmp"))


def test_second_write_failure_removes_new_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original = link_agent_docs._atomic_replace

    def fail_claude(path: Path, content: bytes, mode: int | None = None) -> None:
        if path.name == "CLAUDE.md":
            raise OSError("second replacement failed")
        original(path, content, mode)

    monkeypatch.setattr(link_agent_docs, "_atomic_replace", fail_claude)
    with pytest.raises(AgentDocumentError, match="failed to commit agent documents"):
        ensure_agent_docs(tmp_path)
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".agent" / "knowledge" / "KNOWLEDGE.md").exists()


def test_mixed_create_modify_rollback_and_incomplete_rollback_reporting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    agents = tmp_path / "AGENTS.md"
    original_agents = b"# Existing\n"
    agents.write_bytes(original_agents)
    original = link_agent_docs._atomic_replace

    def fail_commit_and_restore(path: Path, content: bytes, mode: int | None = None) -> None:
        if path.name == "CLAUDE.md":
            raise OSError("commit failed")
        if content == original_agents:
            raise OSError("restore failed")
        original(path, content, mode)

    monkeypatch.setattr(link_agent_docs, "_atomic_replace", fail_commit_and_restore)
    with pytest.raises(AgentDocumentError, match="rollback incomplete") as excinfo:
        ensure_agent_docs(tmp_path)
    assert isinstance(excinfo.value.__cause__, OSError)
    assert not (tmp_path / "CLAUDE.md").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission modes are not meaningful on Windows")
def test_existing_mode_is_preserved(tmp_path: Path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Existing\n", encoding="utf-8")
    agents.chmod(0o640)
    ensure_agent_docs(tmp_path)
    assert stat.S_IMODE(agents.stat().st_mode) == 0o640
    assert not list(tmp_path.glob(".*.map-codebase-*.tmp"))


def test_unchanged_opted_out_and_malformed_docs_never_attempt_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ensure_agent_docs(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("<!-- OPT-OUT MAP-CODEBASE -->\n", encoding="utf-8")

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("write should not be attempted")

    monkeypatch.setattr(link_agent_docs, "_atomic_replace", unexpected)
    ensure_agent_docs(tmp_path)
    (tmp_path / "AGENTS.md").write_text(f"{MANAGED_BEGIN}\n", encoding="utf-8")
    with pytest.raises(AgentDocumentError):
        ensure_agent_docs(tmp_path)


@pytest.mark.parametrize("script", ["build_knowledge.py", "refresh_knowledge.py"])
def test_standalone_finalization_failure_is_concise(sample_repo: Path, script: str):
    (sample_repo / "AGENTS.md").write_text(f"{MANAGED_BEGIN}\n", encoding="utf-8")
    result = _run(script, sample_repo)
    assert result.returncode != 0
    assert "Knowledge artifacts were created, but agent-document finalization failed" in result.stderr
    assert "Traceback" not in result.stderr
    assert (sample_repo / ".agent" / "knowledge" / "manifest.json").is_file()
