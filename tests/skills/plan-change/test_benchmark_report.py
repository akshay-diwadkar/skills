from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "benchmarks" / "reports" / "plan-change-v6.json"
BENCHMARK = ROOT / "tests" / "skills" / "plan-change" / "evals" / "tools" / "benchmark_sealing.py"


def _assert_contract(report: dict) -> None:
    assert report["schema_version"] == 3
    methodology = report["methodology"]
    assert methodology["benchmark_type"] == "targeted sealing microbenchmark"
    assert methodology["end_to_end_native_agent_parity"] == "not_measured"
    assert "benchmark_sealing.py" in report["v6_sealing_microbenchmark"]["command"]
    timings = report["v6_sealing_microbenchmark"]["timings_seconds"]
    assert set(timings) == {"tiny", "standard", "high-risk"}
    assert "sealing only" in report["v6_sealing_microbenchmark"]["label"]


def test_committed_plan_change_benchmark_has_comparable_machine_phases_only() -> None:
    _assert_contract(json.loads(REPORT.read_text(encoding="utf-8")))


@pytest.mark.benchmark
def test_plan_change_benchmark_reproduces_report_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(BENCHMARK), "--iterations", "1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    _assert_contract(json.loads(result.stdout))
