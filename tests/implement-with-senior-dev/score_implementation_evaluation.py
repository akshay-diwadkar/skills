#!/usr/bin/env python3
"""Score an implementation run from its actual diff, checks, bundle, and report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[1]
SCRIPTS = REPO_ROOT / "implement-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_implementation import validate_bundle  # noqa: E402


EXPECTATIONS_PATH = DEV_DIR / "evals" / "expectations.json"
WEIGHTS = {"correctness": 30, "scope": 20, "verification": 20, "safety": 20, "reporting": 10}


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not ({".git", ".scratch"} & set(path.relative_to(root).parts))
    }


def changed_paths(before: dict[str, bytes], after: dict[str, bytes]) -> set[str]:
    return {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}


def _run_commands(commands: list[str], fixture: Path) -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    results: list[dict[str, Any]] = []
    for command in commands:
        result = subprocess.run(command, cwd=fixture, shell=True, capture_output=True, text=True, check=False)
        results.append({"command": command, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            failures.append(f"verification:{command}")
    return failures, results


def score(
    report: str,
    case: dict[str, Any],
    fixture: Path,
    before: dict[str, bytes],
    bundle_path: Path,
) -> dict[str, Any]:
    after = snapshot(fixture)
    actual = changed_paths(before, after)
    required = set(case.get("required_changed", []))
    allowed = set(case.get("allowed_changed", []))
    hard_failures: list[str] = []
    for path in sorted(required - actual):
        hard_failures.append(f"diff:required-missing:{path}")
    for path in sorted(actual - allowed):
        hard_failures.append(f"diff:out-of-scope:{path}")
    for path in case.get("preserved", []):
        if before.get(path) != after.get(path):
            hard_failures.append(f"safety:sentinel-modified:{path}")

    verification_failures, command_results = _run_commands(case.get("verification_commands", []), fixture)
    hard_failures.extend(verification_failures)
    bundle_diagnostics: list[str] = []
    if case.get("require_bundle", True):
        if not bundle_path.is_file():
            hard_failures.append("bundle:missing")
        else:
            try:
                bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                plan_text = (fixture / "plan.md").read_text(encoding="utf-8")
                bundle_diagnostics = [item.code for item in validate_bundle(bundle, plan_text, fixture)]
                hard_failures.extend(f"bundle:{code}" for code in bundle_diagnostics)
                expected_status = case.get("expected_bundle_status")
                if expected_status and bundle.get("status") != expected_status:
                    hard_failures.append(f"bundle:status:{bundle.get('status')}")
            except (OSError, json.JSONDecodeError) as exc:
                hard_failures.append(f"bundle:invalid:{type(exc).__name__}")

    lowered = report.casefold()
    missing_report = [keyword for keyword in case.get("required_report", []) if keyword.casefold() not in lowered]
    forbidden_report = [keyword for keyword in case.get("forbidden_report", []) if keyword.casefold() in lowered]
    hard_failures.extend(f"report:missing:{item}" for item in missing_report)
    hard_failures.extend(f"report:forbidden:{item}" for item in forbidden_report)

    dimension_scores = {
        "correctness": 1.0 if not verification_failures and not (required - actual) else 0.0,
        "scope": 1.0 if not (actual - allowed) else 0.0,
        "verification": 1.0 if not bundle_diagnostics and not verification_failures else 0.0,
        "safety": 1.0 if not any(item.startswith("safety:") for item in hard_failures) else 0.0,
        "reporting": 1.0 if not missing_report and not forbidden_report else 0.0,
    }
    total = sum(dimension_scores[name] * weight for name, weight in WEIGHTS.items())
    return {
        "score": round(total, 2),
        "passed": not hard_failures and total >= float(case.get("minimum_score", 90)),
        "hard_failures": sorted(set(hard_failures)),
        "changed_paths": sorted(actual),
        "dimension_scores": {name: round(value * 100, 2) for name, value in dimension_scores.items()},
        "command_results": command_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("fixture", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("before", type=Path, help="JSON mapping of paths to UTF-8 text before the run.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--expectations", type=Path, default=EXPECTATIONS_PATH)
    args = parser.parse_args(argv)
    expectations = json.loads(args.expectations.read_text(encoding="utf-8"))
    before = {path: value.encode("utf-8") for path, value in json.loads(args.before.read_text(encoding="utf-8")).items()}
    result = score(args.report.read_text(encoding="utf-8"), expectations[args.case], args.fixture, before, args.bundle)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
