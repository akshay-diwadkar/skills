"""Focused end-to-end regressions for final resolver and freshness contracts."""

import json
import subprocess
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from refresh_knowledge import check_freshness, refresh_knowledge
from resolve_task import resolve_task


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _fixture(root: Path) -> Path:
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "service.py").write_text("def retry(): return True\n", encoding="utf-8")
    (root / "tests" / "test_service.py").write_text("from src.service import retry\ndef test_retry(): assert retry()\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("# line-length = 1\n[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    _git(root, "add", "src", "tests", "pyproject.toml")
    _git(root, "commit", "-m", "initial")
    return root / ".agent" / "knowledge"


def test_intent_primary_and_secondary_roles_are_deterministic(tmp_path: Path):
    out = _fixture(tmp_path)
    build_knowledge(tmp_path, out)
    cases = {
        "Implement retry support": ("source", []),
        "Implement retry support and update the tests": ("source", ["test"]),
        "Implement retry support and expose a configuration option": ("source", ["configuration"]),
        "Add retry support, expose its configuration, and update the tests": ("source", ["configuration", "test"]),
        "Fix the assertion in tests/test_service.py": ("test", []),
        "Change Ruff line-length in pyproject.toml": ("configuration", []),
    }
    for task, expected in cases.items():
        intent = resolve_task(tmp_path, task, out)["task_intent"]
        assert (intent["primary_role"], intent["secondary_roles"]) == expected


def test_unignored_knowledge_output_is_never_repository_change(tmp_path: Path):
    out = _fixture(tmp_path)
    build_knowledge(tmp_path, out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["repository"]["dirty"] is False
    assert not any(path.startswith(".agent/") for path in manifest["repository"]["untracked_files"])
    assert check_freshness(tmp_path, out)["status"] == "fresh"
    assert refresh_knowledge(tmp_path, knowledge_dir=out)["mode"] == "none"


def test_custom_output_is_excluded_from_metadata_and_explicit_changes(tmp_path: Path):
    _fixture(tmp_path)
    out = tmp_path / ".cache" / "custom-knowledge"
    build_knowledge(tmp_path, out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["repository"]["dirty"] is False
    assert not any(path.startswith(".cache/custom-knowledge") for path in manifest["repository"]["untracked_files"])
    assert check_freshness(tmp_path, out)["status"] == "fresh"
    assert refresh_knowledge(tmp_path, [".cache/custom-knowledge/manifest.json"], out)["mode"] == "none"


def test_refresh_rebuilds_before_loading_missing_or_invalid_manifest(tmp_path: Path):
    out = _fixture(tmp_path)
    missing = refresh_knowledge(tmp_path, knowledge_dir=out)
    assert missing["mode"] == "full"
    (out / "manifest.json").write_text("{not-json", encoding="utf-8")
    invalid = refresh_knowledge(tmp_path, knowledge_dir=out)
    assert invalid["mode"] == "full"
    assert check_freshness(tmp_path, out)["status"] == "fresh"


def test_explicit_indexed_roles_override_generic_words(tmp_path: Path):
    out = _fixture(tmp_path)
    (tmp_path / "src" / "validator.py").write_text("def validate_response(): return True\n", encoding="utf-8")
    _git(tmp_path, "add", "src/validator.py")
    _git(tmp_path, "commit", "-m", "validator")
    build_knowledge(tmp_path, out)
    cases = {
        "Fix assertion handling in src/validator.py": ("source", []),
        "Fix assertion handling in validate_response": ("source", []),
        "Add a regression test for retry behavior": ("test", []),
        "Add retry support and a regression test": ("source", ["test"]),
        "Add a package.json test script": ("configuration", []),
        "Refactor tests/test_service.py": ("test", []),
        "Refactor the test script in pyproject.toml": ("configuration", []),
    }
    for task, expected in cases.items():
        intent = resolve_task(tmp_path, task, out)["task_intent"]
        assert (intent["primary_role"], intent["secondary_roles"]) == expected
        assert intent["reasons"]


def test_configuration_range_prefers_active_key_over_comment(tmp_path: Path):
    out = _fixture(tmp_path)
    build_knowledge(tmp_path, out)
    target = resolve_task(tmp_path, "Change tool.ruff.line-length in pyproject.toml", out)["targets"][0]
    assert target["start_line"] and target["end_line"] and target["end_line"] >= 3
    assert "configuration_key: tool.ruff.line-length" in target["evidence"]


def test_configuration_ranges_follow_yaml_and_json_ancestry(tmp_path: Path):
    out = _fixture(tmp_path)
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "quality.yml").write_text("jobs:\n  test:\n    strategy:\n      matrix:\n        python: ['3.11']\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"scripts": {"test": "pytest -q"}}\n', encoding="utf-8")
    _git(tmp_path, "add", ".github/workflows/quality.yml", "package.json")
    _git(tmp_path, "commit", "-m", "configs")
    build_knowledge(tmp_path, out)
    yaml_target = resolve_task(tmp_path, "Change jobs.test.strategy.matrix in .github/workflows/quality.yml", out)["targets"][0]
    json_target = resolve_task(tmp_path, "Change scripts.test in package.json", out)["targets"][0]
    assert yaml_target["start_line"] and "configuration_key: jobs.test.strategy.matrix" in yaml_target["evidence"]
    assert json_target["start_line"] and "configuration_key: scripts.test" in json_target["evidence"]
