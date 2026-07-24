#!/usr/bin/env python3
"""Run provider-neutral implementation evaluations in disposable Git repositories."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import score_implementation_evaluation

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SKILL_PATH = REPO_ROOT / "skills" / "engineering" / "implement-with-senior-dev"


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def invoke_adapter(command: list[str], request: dict[str, Any], timeout_seconds: int, cwd: Path) -> str:
    result = subprocess.run(
        command,
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"adapter returned malformed JSON: {exc}") from exc
    report = response.get("implementation_report_markdown")
    if not isinstance(report, str) or not report.strip():
        raise RuntimeError("adapter response must contain non-empty implementation_report_markdown")
    return report


def _init_repo(fixture: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=fixture, check=True)
    subprocess.run(["git", "config", "user.email", "eval@example.com"], cwd=fixture, check=True)
    subprocess.run(["git", "config", "user.name", "Eval"], cwd=fixture, check=True)
    subprocess.run(["git", "add", "."], cwd=fixture, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture baseline"], cwd=fixture, check=True)
    exclude = fixture / ".git" / "info" / "exclude"
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write("\n.scratch/\n")


def _apply_dirty_setup(fixture: Path, setup: list[dict[str, str]]) -> None:
    for item in setup:
        path = fixture / item["path"]
        if "content" in item:
            path.write_text(item["content"], encoding="utf-8")
        else:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(item.get("append", ""))


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
    source_before = tree_hash(source_fixture)
    with tempfile.TemporaryDirectory(prefix=f"implement-eval-{case_id}-") as temporary:
        fixture = Path(temporary) / case_id
        shutil.copytree(source_fixture, fixture)
        _init_repo(fixture)
        _apply_dirty_setup(fixture, case.get("dirty_setup", []))
        before = score_implementation_evaluation.snapshot(fixture)
        bundle_path = fixture / ".scratch" / "implement-with-senior-dev" / "eval" / "implementation.json"
        request = {
            "case_id": case_id,
            "model_label": model_label,
            "prompt": (fixture / "prompt.md").read_text(encoding="utf-8"),
            "repo_root": str(fixture),
            "skill_path": str(SKILL_PATH),
            "plan_path": str(fixture / "plan.md"),
            "run_bundle_path": str(bundle_path),
        }
        report = invoke_adapter(command, request, timeout_seconds, fixture)
        result = score_implementation_evaluation.score(report, case, fixture, before, bundle_path)
    if tree_hash(source_fixture) != source_before:
        result["hard_failures"] = sorted({*result["hard_failures"], "fixture:source-mutated"})
        result["passed"] = False
    case_dir = output_dir / model_label / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / f"run-{run_number}.md").write_text(report, encoding="utf-8")
    (case_dir / f"run-{run_number}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"case_id": case_id, "model_label": model_label, "run": run_number, **result}


def summarize(results: list[dict[str, Any]], model_labels: list[str]) -> tuple[bool, dict[str, dict[str, Any]]]:
    summaries: dict[str, dict[str, Any]] = {}
    passed = True
    for model_label in model_labels:
        model_results = [result for result in results if result["model_label"] == model_label]
        scores = [float(result["score"]) for result in model_results]
        hard_failures = sorted({failure for result in model_results for failure in result["hard_failures"]})
        median_score = statistics.median(scores)
        minimum_score = min(scores)
        model_passed = not hard_failures and median_score >= 90 and minimum_score >= 80
        summaries[model_label] = {
            "median_score": median_score,
            "minimum_score": minimum_score,
            "hard_failures": hard_failures,
            "runs": len(model_results),
            "passed": model_passed,
        }
        passed = passed and model_passed
    return passed, summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-command", nargs="+", required=True)
    parser.add_argument("--model-label", action="append", required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / ".scratch" / "implement-with-senior-dev-evals")
    parser.add_argument("--expectations", type=Path, default=score_implementation_evaluation.EXPECTATIONS_PATH)
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
                results.append(run_case(args.adapter_command, case_id, case, model_label, run_number, args.timeout_seconds, args.output_dir))
    passed, summaries = summarize(results, args.model_label)
    report = {"passed": passed, "models": summaries, "results": results}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "models": summaries}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
