import subprocess
import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from knowledge import discovery


def test_artifact_byte_determinism(tmp_path: Path):
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"

    for r in [repo1, repo2]:
        src_dir = r / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "b.py").write_text("class B:\n    pass\n", encoding="utf-8")
        (src_dir / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")

    out_dir1 = repo1 / ".agent" / "knowledge"
    out_dir2 = repo2 / ".agent" / "knowledge"

    build_knowledge(repo1, out_dir1)
    build_knowledge(repo2, out_dir2)

    for fname in ["repo-map.json", "symbols.json", "relationships.json", "manifest.json"]:
        b1 = (out_dir1 / fname).read_bytes()
        b2 = (out_dir2 / fname).read_bytes()
        assert b1 == b2, f"Determinism mismatch in {fname}"


def test_git_timeout_uses_filesystem_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")

    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("git", 5)

    monkeypatch.setattr(discovery.subprocess, "run", timeout)
    result = build_knowledge(repo, repo / ".agent" / "knowledge")

    assert result["files_indexed"] == 1
