from __future__ import annotations

import importlib.util
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


def test_each_skill_runs_in_an_independent_mypy_process() -> None:
    runner = load_runner()

    catalog = {
        "skills": [
            {
                "name": "first-skill",
                "path": "skills/engineering/first-skill",
                "tests": "tests/skills/first-skill",
            },
            {
                "name": "second-skill",
                "path": "skills/engineering/second-skill",
                "tests": "tests/skills/second-skill",
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
        "skill: first-skill",
        "skill: second-skill",
        "repository tooling",
    ]
