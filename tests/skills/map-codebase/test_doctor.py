import importlib.metadata
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
CLI_PATH = ROOT / "skills" / "engineering" / "map-codebase" / "scripts" / "cli.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("map_codebase_cli", CLI_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_reports_success_with_compatible_dependencies(tmp_path: Path, capsys) -> None:
    module = _module()
    status = module.run_doctor(
        tmp_path,
        version_lookup=lambda name: "4.22.0" if name == "jsonschema" else "0.22.0",
    )
    output = capsys.readouterr().out
    assert status == 0
    assert "[OK] Repository root:" in output
    assert "[OK] Dependencies: 12 requirement(s) installed" in output


def test_doctor_reports_invalid_repository_path_without_traceback(tmp_path: Path, capsys) -> None:
    module = _module()
    status = module.run_doctor(
        tmp_path / "missing",
        version_lookup=lambda name: "4.22.0" if name == "jsonschema" else "0.22.0",
    )
    output = capsys.readouterr().out
    assert status == 1
    assert "pass an existing directory with --repo-root" in output
    assert "Traceback" not in output


def test_doctor_reports_missing_dependency_with_install_command(tmp_path: Path, capsys) -> None:
    module = _module()

    def lookup(name: str) -> str:
        if name == "jsonschema":
            raise importlib.metadata.PackageNotFoundError(name)
        return "0.22.0"

    status = module.run_doctor(tmp_path, version_lookup=lookup)
    output = capsys.readouterr().out
    assert status == 1
    assert "Missing dependencies: jsonschema" in output
    assert "python -m pip install -r" in output
    assert "Traceback" not in output


def test_non_doctor_command_fails_actionably_without_jsonschema(tmp_path: Path) -> None:
    blocker = tmp_path / "blocked-import"
    blocker.mkdir()
    (blocker / "jsonschema.py").write_text(
        'raise ImportError("jsonschema blocked for regression test")\n',
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(blocker), environment.get("PYTHONPATH", "")) if value
    )

    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "status",
            "--repo-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode == 1
    assert 'Missing required dependency "jsonschema"' in result.stderr
    assert "python -m pip install -r" in result.stderr
    assert "Traceback" not in result.stderr
