from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.benchmark
def test_representative_comparison_and_committed_results_are_current() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "tests/skills/map-codebase/run_benchmark.py",
            "--profile",
            "representative",
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.benchmark
@pytest.mark.benchmark_slow
def test_full_comparison_and_committed_results_are_current() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "tests/skills/map-codebase/run_benchmark.py",
            "--profile",
            "full",
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
