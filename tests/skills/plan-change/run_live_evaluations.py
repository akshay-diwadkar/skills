#!/usr/bin/env python3
"""Run isolated, provider-neutral behavioral plan-change evaluations."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import validate_plan  # noqa: E402
from score_plan_evaluation import release_gate, score_expectations

SCENARIOS = Path(__file__).with_name("evals") / "v5_scenarios.json"
EXPECTATIONS = Path(__file__).with_name("evals") / "expectations.json"
FIXTURES = Path(__file__).with_name("evals") / "fixtures"


def run_adapter(command: list[str], request: dict[str, Any]) -> str:
    result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    response = json.loads(result.stdout)
    if not isinstance(response, dict) or not isinstance(response.get("plan_markdown"), str):
        raise RuntimeError("adapter stdout must be JSON with string plan_markdown")
    return response["plan_markdown"]


def run_downstream_adapter(command: list[str], request: dict[str, Any]) -> bool:
    result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"downstream adapter exited {result.returncode}: {result.stderr.strip()}")
    response = json.loads(result.stdout)
    if not isinstance(response, dict) or not isinstance(response.get("passed"), bool):
        raise RuntimeError("downstream adapter stdout must be JSON with boolean passed")
    return response["passed"]


def evaluate(
    adapter: list[str], output: Path, repetitions: int = 3, model_label: str = "unknown", downstream_adapter: list[str] | None = None
) -> dict[str, Any]:
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    expectations = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    runs: list[dict[str, Any]] = []
    for family, names in scenarios["scenario_families"].items():
        for name in names:
            fixture = FIXTURES / name
            if not fixture.is_dir() or name not in expectations:
                raise RuntimeError(f"scenario {name} must have a fixture and expectations")
            for attempt in range(repetitions):
                with tempfile.TemporaryDirectory(prefix="plan-change-eval-") as temp:
                    repo = Path(temp) / "repo"
                    shutil.copytree(fixture, repo)
                    before = sorted((p.relative_to(repo).as_posix(), p.read_bytes()) for p in repo.rglob("*") if p.is_file())
                    prompt = (repo / "prompt.md").read_text(encoding="utf-8")
                    plan = run_adapter(adapter, {"scenario": name, "family": family, "repo_root": str(repo), "prompt": prompt})
                    after = sorted((p.relative_to(repo).as_posix(), p.read_bytes()) for p in repo.rglob("*") if p.is_file())
                    _parsed, diagnostics = validate_plan(plan, repo, require_finalized=True)
                    score, dimensions, missing = score_expectations(plan, expectations[name])
                    forbidden = [value for value in expectations[name].get("forbidden", []) if value.casefold() in plan.casefold()]
                    downstream_status = (
                        "passed"
                        if downstream_adapter
                        and run_downstream_adapter(
                            downstream_adapter,
                            {"scenario": name, "family": family, "repo_root": str(repo), "plan_markdown": plan},
                        )
                        else "failed"
                        if downstream_adapter
                        else "not-applicable"
                    )
                    hard_failures = ([] if before == after else ["repository-mutation"])
                    hard_failures.extend(f"contract:{item.code}" for item in diagnostics)
                    hard_failures.extend(f"missing:{item}" for item in missing)
                    hard_failures.extend(f"forbidden:{item}" for item in forbidden)
                    runs.append({
                        "scenario": name, "family": family, "attempt": attempt + 1, "model_label": model_label,
                        "raw_plan": plan, "repository_mutation": before != after, "score": score,
                        "dimension_scores": dimensions, "hard_failures": sorted(set(hard_failures)),
                        "failures": sorted(set(hard_failures)), "downstream_status": downstream_status,
                    })
    report = {
        "contract_version": 5,
        "runs": runs,
        "release_failures": release_gate(runs),
        "reliability_claim": None,
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model-label", default="unknown")
    parser.add_argument("--downstream-adapter", nargs="+")
    args = parser.parse_args()
    evaluate(args.adapter, args.output, args.repetitions, args.model_label, args.downstream_adapter)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
