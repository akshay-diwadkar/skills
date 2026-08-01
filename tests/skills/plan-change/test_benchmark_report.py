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
    assert report["schema_version"] == 2
    methodology = report["methodology"]
    assert methodology["benchmark_type"] == "machine-pipeline microbenchmark"
    assert methodology["end_to_end_native_agent_parity"] == "not_measured"
    assert set(methodology["parity_requires"]) == {
        "same model and effort",
        "same repository and request",
        "same environment",
        "complete tool-call accounting",
        "complete token accounting",
    }
    assert report["historical_v5_suite_baseline"]["comparable_to_machine_pipeline"] is False
    machine_pipeline = report["machine_pipeline_comparison"]
    assert "benchmark_sealing.py" in machine_pipeline["command"]
    comparison = machine_pipeline["timings_seconds"]
    assert set(comparison) == {"tiny", "standard", "high-risk"}
    for tier in comparison.values():
        assert set(tier["v5"]) == {
            "prepare",
            "validate",
            "finalize",
            "aggregate_machine_pipeline",
        }
        assert set(tier["v6"]) == {"seal"}
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
