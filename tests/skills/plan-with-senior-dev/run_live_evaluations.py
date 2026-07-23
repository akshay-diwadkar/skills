#!/usr/bin/env python3
"""Run opt-in plan-skill evaluations through a provider-neutral adapter."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SKILL_PATH = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev"
SCORER_PATH = DEV_DIR / "score_plan_evaluation.py"
SCORER_SPEC = importlib.util.spec_from_file_location("plan_with_senior_dev_score", SCORER_PATH)
if SCORER_SPEC is None or SCORER_SPEC.loader is None:
    raise RuntimeError(f"cannot load scorer from {SCORER_PATH}")
score_plan_evaluation = importlib.util.module_from_spec(SCORER_SPEC)
SCORER_SPEC.loader.exec_module(score_plan_evaluation)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def invoke_adapter(command: list[str], request: dict[str, Any], timeout_seconds: int) -> str:
    result = subprocess.run(
        command,
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"adapter returned malformed JSON: {exc}") from exc
    plan = response.get("plan_markdown")
    if not isinstance(plan, str) or not plan.strip():
        raise RuntimeError("adapter response must contain non-empty plan_markdown")
    return plan


def run_case(
    command: list[str],
    case_id: str,
    case: dict[str, Any],
    model_label: str,
    run_number: int,
    timeout_seconds: int,
    output_dir: Path,
) -> dict[str, Any]:
    source_fixture = DEV_DIR / "evals" / "fixtures" / case_id
    with tempfile.TemporaryDirectory(prefix=f"plan-eval-{case_id}-") as temporary:
        fixture = Path(temporary) / case_id
        shutil.copytree(source_fixture, fixture)
        before = tree_hash(fixture)
        request = {
            "case_id": case_id,
            "model_label": model_label,
            "prompt": (fixture / "prompt.md").read_text(encoding="utf-8"),
            "repo_root": str(fixture),
            "skill_path": str(SKILL_PATH),
        }
        plan = invoke_adapter(command, request, timeout_seconds)
        after = tree_hash(fixture)
        result = score_plan_evaluation.score(plan, case, fixture)
        if before != after:
            result["hard_failures"] = sorted({*result["hard_failures"], "fixture:mutated"})
            result["passed"] = False

    case_dir = output_dir / model_label / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / f"run-{run_number}.md").write_text(plan, encoding="utf-8")
    (case_dir / f"run-{run_number}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"case_id": case_id, "model_label": model_label, "run": run_number, **result}


def summarize(results: list[dict[str, Any]], model_labels: list[str]) -> tuple[bool, dict[str, dict[str, Any]]]:
    summaries: dict[str, dict[str, Any]] = {}
    passed = True
    for model_label in model_labels:
        model_results = [item for item in results if item["model_label"] == model_label]
        scores = [float(item["score"]) for item in model_results]
        hard_failures = sorted({failure for item in model_results for failure in item["hard_failures"]})
        blueprint_scores = [float(item["dimension_scores"]["blueprint"]) for item in model_results]
        median_score = statistics.median(scores)
        minimum_score = min(scores)
        minimum_blueprint_score = min(blueprint_scores)
        summary = {
            "median_score": median_score,
            "minimum_score": minimum_score,
            "minimum_blueprint_score": minimum_blueprint_score,
            "hard_failures": hard_failures,
            "runs": len(model_results),
        }
        summary["passed"] = (
            not hard_failures
            and median_score >= 90
            and minimum_score >= 80
            and minimum_blueprint_score == 100
        )
        summaries[model_label] = summary
        passed = passed and bool(summary["passed"])
    return passed, summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-command", nargs="+", required=True)
    parser.add_argument("--model-label", action="append", required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / ".scratch" / "plan-with-senior-dev-evals")
    parser.add_argument("--expectations", type=Path, default=score_plan_evaluation.EXPECTATIONS_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")
    expectations = json.loads(args.expectations.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for model_label in args.model_label:
        for case_id, case in expectations.items():
            for run_number in range(1, args.runs + 1):
                results.append(run_case(
                    args.adapter_command,
                    case_id,
                    case,
                    model_label,
                    run_number,
                    args.timeout_seconds,
                    args.output_dir,
                ))
    passed, summaries = summarize(results, args.model_label)
    report = {"passed": passed, "models": summaries, "results": results}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "models": summaries}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
