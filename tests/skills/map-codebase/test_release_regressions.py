"""Regression coverage for release-hardening edge cases."""

import json
import subprocess
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from refresh_knowledge import check_freshness, refresh_knowledge
from resolve_task import resolve_task


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(root: Path) -> Path:
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "main.py").write_text("def validate_body_length():\n    return True\n", encoding="utf-8")
    _git(root, "add", "main.py")
    _git(root, "commit", "-m", "initial")
    return root / ".agent" / "knowledge"


def test_disabled_untracked_never_enters_refresh(tmp_path: Path):
    out = _repo(tmp_path)
    (tmp_path / ".codebase-knowledge.toml").write_text("include_untracked = false\n", encoding="utf-8")
    build_knowledge(tmp_path, out)
    (tmp_path / "new.py").write_text("def new(): pass\n", encoding="utf-8")
    assert check_freshness(tmp_path, out)["status"] == "fresh"
    assert refresh_knowledge(tmp_path, ["new.py"], out)["mode"] == "none"
    paths = {x["path"] for x in json.loads((out / "repo-map.json").read_text())["files"]}
    assert "new.py" not in paths
    _git(tmp_path, "add", "new.py")
    assert "new.py" in check_freshness(tmp_path, out)["changed_files"]
    refresh_knowledge(tmp_path, knowledge_dir=out)
    assert "new.py" in {x["path"] for x in json.loads((out / "repo-map.json").read_text())["files"]}


def test_configuration_ranges_roles_and_directional_impacts(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "primary.py").write_text("from src.dependency import dep\ndef reset_password(): return dep()\ndef validate_body_length(): return True\ndef line_parser(): return True\ndef preferences_setting(): return True\n", encoding="utf-8")
    (tmp_path / "src" / "dependency.py").write_text("def dep(): return True\n", encoding="utf-8")
    (tmp_path / "src" / "caller.py").write_text("from src.primary import reset_password\n", encoding="utf-8")
    (tmp_path / "tests" / "test_helper.py").write_text("def fixture(): pass\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("# line-length = 1\n[tool.ruff]\nline-length = 100\n[tool.pytest.ini_options]\naddopts = '-q'\n", encoding="utf-8")
    out = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out)
    for task in ("Fix request body length validation", "Improve line parser performance", "Update the setting value returned by the preferences service"):
        assert resolve_task(tmp_path, task, out)["targets"][0]["role"] == "source"
    config = resolve_task(tmp_path, "Change Ruff line-length in pyproject.toml", out)
    assert config["targets"][0]["role"] == "configuration"
    assert 1 <= config["targets"][0]["start_line"] <= 3
    assert resolve_task(tmp_path, "Fix pytest fixture discovery in tests/test_helper.py", out)["targets"][0]["role"] == "test"
    impacts = resolve_task(tmp_path, "Update callers affected by reset_password", out, phase=3)["targets"]
    evidence = {item["path"]: item["evidence"] for item in impacts}
    assert "dependency_of: src/primary.py" in evidence["src/dependency.py"]
    assert "imports: src/primary.py" in evidence["src/caller.py"]
    assert all(f"imports: {path}" not in values for path, values in evidence.items())


def test_metadata_only_refresh_on_excluded_untracked(tmp_path: Path):
    out = _repo(tmp_path)
    build_knowledge(tmp_path, out)
    before = {name: (out / name).read_bytes() for name in ("repo-map.json", "symbols.json", "relationships.json")}
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "note.py").write_text("ignored\n", encoding="utf-8")
    state = check_freshness(tmp_path, out)
    assert state["status"] == "fresh" and state["repository_metadata_changed"]
    assert refresh_knowledge(tmp_path, knowledge_dir=out)["mode"] == "metadata-only"
    assert before == {name: (out / name).read_bytes() for name in before}
    assert check_freshness(tmp_path, out)["status"] == "fresh"
