#!/usr/bin/env python3
"""Run optional isolated, provider-neutral design-codebase evaluations."""

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
SKILL = ROOT / "skills" / "engineering" / "design-codebase"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
from handoff_contract import validate_handoff  # noqa: E402
from score_design_evaluation import score_expectations  # noqa: E402

EVALS = Path(__file__).with_name("evals")
FIXTURES = EVALS / "fixtures"
EXPECTATIONS = EVALS / "expectations.json"


def run_adapter(command: list[str], request: dict[str, Any]) -> str:
    result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    response = json.loads(result.stdout)
    if not isinstance(response, dict) or not isinstance(response.get("handoff_markdown"), str):
        raise RuntimeError("adapter stdout must be JSON with string handoff_markdown")
    return response["handoff_markdown"]


def _snapshot(repo: Path) -> list[tuple[str, bytes]]:
    return sorted((path.relative_to(repo).as_posix(), path.read_bytes()) for path in repo.rglob("*") if path.is_file())


def evaluate(
    adapter: list[str],
    output: Path,
    *,
    scenarios: list[str] | None = None,
    model_label: str = "unknown",
) -> dict[str, Any]:
    expectations = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    selected = scenarios or sorted(expectations)
    runs: list[dict[str, Any]] = []
    for scenario in selected:
        fixture = FIXTURES / scenario
        if scenario not in expectations or not fixture.is_dir():
            raise RuntimeError(f"scenario {scenario} must have a fixture and expectations")
        with tempfile.TemporaryDirectory(prefix="design-codebase-eval-") as temp:
            repo = Path(temp) / "repo"
            shutil.copytree(fixture, repo)
            before = _snapshot(repo)
            handoff = run_adapter(
                adapter,
                {
                    "scenario": scenario,
                    "repo_root": str(repo),
                    "prompt": (repo / "prompt.md").read_text(encoding="utf-8"),
                    "skill_root": str(SKILL),
                },
            )
            after = _snapshot(repo)
            _parsed, diagnostics = validate_handoff(handoff, repo)
            score = score_expectations(handoff, expectations[scenario])
            hard_failures = [f"contract:{item.code}" for item in diagnostics]
            if before != after:
                hard_failures.append("repository-mutation")
            if score["missing_concepts"]:
                hard_failures.extend(f"missing-concept:{item}" for item in score["missing_concepts"])
            if not score["outcome_matched"]:
                hard_failures.append("outcome-missing")
            hard_failures.extend(f"forbidden:{item}" for item in score["forbidden"])
            runs.append(
                {
                    "scenario": scenario,
                    "model_label": model_label,
                    "score": score["score"],
                    "repository_mutation": before != after,
                    "hard_failures": sorted(set(hard_failures)),
                    "raw_handoff": handoff,
                }
            )
    report = {"contract_version": 1, "runs": runs}
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenario", action="append", dest="scenarios")
    parser.add_argument("--model-label", default="unknown")
    args = parser.parse_args()
    evaluate(args.adapter, args.output, scenarios=args.scenarios, model_label=args.model_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
