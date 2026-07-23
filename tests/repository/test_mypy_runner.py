from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_mypy", REPO_ROOT / "tools" / "validation" / "run_mypy.py"
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_catalog_skill_and_tooling_runs_in_separate_invocations() -> None:
    runner = load_runner()

    catalog = {
        "skills": [
            {
                "name": "skill-one",
                "path": "skills/engineering/skill-one",
                "tests": "tests/skills/skill-one",
            },
            {
                "name": "skill-two",
                "path": "skills/engineering/skill-two",
                "tests": "tests/skills/skill-two",
            },
        ]
    }

    with (
        patch.object(runner, "load_catalog", return_value=catalog),
        patch.object(runner, "run_mypy_group", return_value=True) as run_group,
    ):
        assert runner.main() == 0

    labels = [call.args[0] for call in run_group.call_args_list]

    assert labels == [
        "skill: skill-one",
        "skill: skill-two",
        "repository tooling",
    ]


def test_failure_in_one_skill_does_not_prevent_later_skills() -> None:
    runner = load_runner()

    catalog = {
        "skills": [
            {
                "name": "failing-skill",
                "path": "skills/engineering/failing-skill",
                "tests": "tests/skills/failing-skill",
            },
            {
                "name": "passing-skill",
                "path": "skills/engineering/passing-skill",
                "tests": "tests/skills/passing-skill",
            },
        ]
    }

    def mock_run_group(label: str, targets: list[str]) -> bool:
        if "failing-skill" in label:
            return False
        return True

    with (
        patch.object(runner, "load_catalog", return_value=catalog),
        patch.object(runner, "run_mypy_group", side_effect=mock_run_group) as run_group,
    ):
        exit_code = runner.main()
        assert exit_code == 1

    assert run_group.call_count == 3
    labels = [call.args[0] for call in run_group.call_args_list]
    assert labels == ["skill: failing-skill", "skill: passing-skill", "repository tooling"]


def test_subprocess_command_format() -> None:
    runner = load_runner()

    with (
        patch.object(runner, "has_python_files", return_value=True),
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        success = runner.run_mypy_group("test-group", ["skills/engineering/test-skill"])
        assert success is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable
        assert cmd[1:4] == ["-m", "mypy", "--no-incremental"]
        assert "skills/engineering/test-skill" in cmd


def test_missing_optional_paths_are_skipped() -> None:
    runner = load_runner()

    def mock_exists(self: Path) -> bool:
        return "non-existent" not in str(self)

    with (
        patch.object(runner, "has_python_files", return_value=True),
        patch("pathlib.Path.exists", mock_exists),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        success = runner.run_mypy_group(
            "test-group",
            ["skills/engineering/existing", "skills/engineering/non-existent"],
        )
        assert success is True
        cmd = mock_run.call_args[0][0]
        assert "skills/engineering/existing" in cmd
        assert "skills/engineering/non-existent" not in cmd


def test_malformed_catalog_handling() -> None:
    runner = load_runner()

    malformed_catalogs = [
        "not a dict",
        {"skills": "not a list"},
        {"skills": [{"path": "missing_name"}]},
    ]

    for cat in malformed_catalogs:
        with patch.object(runner, "load_catalog", return_value=cat):
            assert runner.main() == 1
