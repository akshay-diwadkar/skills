#!/usr/bin/env python3
"""Run blinded native-versus-plan-change-v6 evaluations through JSON adapters."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
SKILL = ROOT / "skills" / "engineering" / "plan-change"
SCENARIOS = Path(__file__).with_name("v6_scenarios.json")
DIMENSIONS = (
    "change_scope",
    "root_cause",
    "implementation_specificity",
    "propagation_completeness",
    "boundary_and_risk",
    "test_completeness",
    "internal_consistency",
    "evidence_validity",
    "fabricated_claim_rate",
    "implementation_readiness",
)


def call_adapter(command: list[str], payload: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(command, input=json.dumps(payload), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError("adapter response must be an object")
    return value


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95 + 0.999) - 1))]


def evaluate(adapter: list[str], judge: list[str], model: str, repetitions: int) -> dict[str, Any]:
    manifest = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    runs: list[dict[str, Any]] = []
    fixtures = Path(__file__).with_name("fixtures")
    for family, names in manifest["scenario_families"].items():
        for name in names:
            prompt = (fixtures / name / "prompt.md").read_text(encoding="utf-8")
            for attempt in range(1, repetitions + 1):
                pair: dict[str, Any] = {"family": family, "scenario": name, "attempt": attempt}
                for condition in ("native", "skill"):
                    response = call_adapter(
                        adapter,
                        {
                            "model_label": model,
                            "condition": condition,
                            "load_skill": condition == "skill",
                            "skill_root": str(SKILL) if condition == "skill" else None,
                            "repo_root": str(fixtures / name),
                            "prompt": prompt,
                        },
                    )
                    plan = response.get("plan_markdown")
                    metrics = response.get("metrics")
                    if not isinstance(plan, str) or not isinstance(metrics, dict):
                        raise ValueError("adapter requires plan_markdown and metrics")
                    scores = call_adapter(judge, {"prompt": prompt, "plan_markdown": plan, "dimensions": DIMENSIONS})
                    if set(scores) != set(DIMENSIONS):
                        raise ValueError("judge must score every dimension")
                    pair[condition] = {"metrics": metrics, "quality": statistics.mean(float(scores[key]) for key in DIMENSIONS), "scores": scores}
                runs.append(pair)
    runtime_ratios = [run["skill"]["metrics"]["wall_clock_ms"] / run["native"]["metrics"]["wall_clock_ms"] for run in runs]
    token_ratios = [
        (run["skill"]["metrics"]["input_tokens"] + run["skill"]["metrics"]["output_tokens"])
        / (run["native"]["metrics"]["input_tokens"] + run["native"]["metrics"]["output_tokens"])
        for run in runs
    ]
    summary = {
        "median_runtime_ratio": statistics.median(runtime_ratios),
        "p95_runtime_ratio": percentile95(runtime_ratios),
        "median_total_token_ratio": statistics.median(token_ratios),
        "repository_wide_script_searches": sum(run["skill"]["metrics"]["repository_wide_script_searches"] for run in runs),
        "median_successful_seal_attempts": statistics.median(run["skill"]["metrics"]["seal_attempts"] for run in runs),
        "cited_evidence_validity": statistics.mean(run["skill"]["metrics"]["evidence_valid"] for run in runs),
        "quality_score_skill": statistics.mean(run["skill"]["quality"] for run in runs),
        "quality_score_native": statistics.mean(run["native"]["quality"] for run in runs),
    }
    gates = manifest["acceptance_gates"]
    failures = []
    if summary["median_runtime_ratio"] > gates["median_runtime_ratio_max"]:
        failures.append("median_runtime_ratio")
    if summary["p95_runtime_ratio"] > gates["p95_runtime_ratio_max"]:
        failures.append("p95_runtime_ratio")
    if summary["median_total_token_ratio"] > gates["median_total_token_ratio_max"]:
        failures.append("median_total_token_ratio")
    if summary["repository_wide_script_searches"] != 0:
        failures.append("repository_wide_script_searches")
    if summary["median_successful_seal_attempts"] != 1:
        failures.append("median_successful_seal_attempts")
    if summary["cited_evidence_validity"] != 1.0:
        failures.append("cited_evidence_validity")
    if summary["quality_score_skill"] <= summary["quality_score_native"]:
        failures.append("quality_score_skill")
    return {"schema_version": 1, "model_label": model, "summary": summary, "failures": failures, "runs": runs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", nargs="+", required=True)
    parser.add_argument("--judge-adapter", nargs="+", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.adapter, args.judge_adapter, args.model, args.repetitions)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return int(bool(report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
