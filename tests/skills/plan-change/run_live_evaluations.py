#!/usr/bin/env python3
"""Run isolated, provider-neutral plan-change evaluation scenarios."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from score_plan_evaluation import release_gate

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = Path(__file__).with_name("evals") / "v5_scenarios.json"
FIXTURES = Path(__file__).with_name("evals") / "fixtures"


def score_plan(plan: str, family: str, mutated: bool) -> tuple[int, int, list[str]]:
    """Score contract-bearing output without coupling evaluations to a provider."""
    required = ("<!-- plan-contract: 5 -->", "## Outcome and Scope", "## Evidence Ledger", "## Traceability", "SC-", "CH-", "T-")
    misses = [item for item in required if item not in plan]
    score = max(0, 100 - 12 * len(misses) - (100 if mutated else 0))
    blueprint = 100
    if family in {"standard", "high-risk"} and "### Execution Blueprint:" not in plan:
        blueprint = 0
        misses.append("execution blueprint")
    return score, blueprint, misses


def run_adapter(command: list[str], request: dict[str, Any]) -> str:
    result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    response = json.loads(result.stdout)
    if not isinstance(response, dict) or not isinstance(response.get("plan_markdown"), str):
        raise RuntimeError("adapter stdout must be JSON with string plan_markdown")
    return response["plan_markdown"]


def evaluate(adapter: list[str], output: Path, repetitions: int = 3, model_label: str = "unknown") -> dict[str, Any]:
    contract = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    runs: list[dict[str, Any]] = []
    for family, names in contract["scenario_families"].items():
        for name in names:
            fixture = FIXTURES / name
            for attempt in range(repetitions):
                with tempfile.TemporaryDirectory(prefix="plan-change-eval-") as temp:
                    repo = Path(temp) / "repo"
                    if fixture.is_dir():
                        shutil.copytree(fixture, repo)
                    else:
                        repo.mkdir()
                    before = sorted(
                        (p.relative_to(repo).as_posix(), p.read_bytes()) for p in repo.rglob("*") if p.is_file()
                    )
                    prompt = (
                        (repo / "prompt.md").read_text(encoding="utf-8") if (repo / "prompt.md").is_file() else name
                    )
                    plan = run_adapter(
                        adapter, {"scenario": name, "family": family, "repo_root": str(repo), "prompt": prompt}
                    )
                    after = sorted(
                        (p.relative_to(repo).as_posix(), p.read_bytes()) for p in repo.rglob("*") if p.is_file()
                    )
                    score, blueprint_score, failures = score_plan(plan, family, before != after)
                    run = {
                        "scenario": name,
                        "family": family,
                        "attempt": attempt + 1,
                        "model_label": model_label,
                        "raw_plan": plan,
                        "repository_mutation": before != after,
                        "score": score,
                        "blueprint_score": blueprint_score,
                        "hard_failures": int(before != after or bool(failures and score < 90)),
                        "failures": failures,
                    }
                    runs.append(run)
    report = {"contract_version": 5, "runs": runs, "release_failures": release_gate(runs), "terra_medium_run": model_label.lower() == "terra-medium"}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model-label", default="unknown")
    args = parser.parse_args()
    evaluate(args.adapter, args.output, args.repetitions, args.model_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
