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


def run_adapter(command: list[str], request: dict[str, Any]) -> str:
    result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    response = json.loads(result.stdout)
    if not isinstance(response, dict) or not isinstance(response.get("plan_markdown"), str):
        raise RuntimeError("adapter stdout must be JSON with string plan_markdown")
    return response["plan_markdown"]


def evaluate(adapter: list[str], output: Path, repetitions: int = 3) -> dict[str, Any]:
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
                    run = {
                        "scenario": name,
                        "family": family,
                        "attempt": attempt + 1,
                        "raw_plan": plan,
                        "repository_mutation": before != after,
                        "score": 0,
                        "blueprint_score": 0,
                        "hard_failures": int(before != after),
                    }
                    runs.append(run)
    report = {"contract_version": 5, "runs": runs, "release_failures": release_gate(runs), "terra_medium_run": False}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    evaluate(args.adapter, args.output, args.repetitions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
