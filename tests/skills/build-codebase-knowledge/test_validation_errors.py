"""Validation failures retain their original diagnostics through the CLIs."""

import subprocess
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import validate_knowledge as validation_module
from validate_knowledge import validate_knowledge


def test_validation_preserves_toml_parse_error(tmp_path: Path):
    (tmp_path / ".codebase-knowledge.toml").write_text("output_dir = [\n", encoding="utf-8")

    result = validate_knowledge(tmp_path)

    assert result["status"] == "invalid"
    assert result["errors"][0].startswith("Failed to parse configuration file")
    assert "knowledge output must be inside repository" not in result["errors"][0]


def test_validation_preserves_missing_weight_error(tmp_path: Path, monkeypatch):
    def fail_load_config(_root: Path) -> dict:
        raise ValueError("weights is missing required values: exact_symbol")

    monkeypatch.setattr(validation_module, "load_config", fail_load_config)

    result = validate_knowledge(tmp_path)

    assert result["errors"] == ["weights is missing required values: exact_symbol"]


def test_validation_preserves_unsafe_output_error(tmp_path: Path):
    result = validate_knowledge(tmp_path, tmp_path.parent / "outside-knowledge")

    assert result["errors"] == ["knowledge output must be inside repository"]


def test_validation_clis_report_errors_on_stderr_without_traceback(tmp_path: Path):
    (tmp_path / ".codebase-knowledge.toml").write_text("output_dir = [\n", encoding="utf-8")
    commands = [
        [sys.executable, str(SKILL_SCRIPTS / "cli.py"), "validate", "--repo-root", str(tmp_path)],
        [sys.executable, str(SKILL_SCRIPTS / "validate_knowledge.py"), "--repo-root", str(tmp_path)],
    ]

    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)

        assert completed.returncode == 1
        assert "Failed to parse configuration file" in completed.stderr
        assert "Traceback" not in completed.stderr
