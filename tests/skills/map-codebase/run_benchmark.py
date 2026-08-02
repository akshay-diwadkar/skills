#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from benchmark_runner import (  # noqa: E402
    REPORT,
    REPRESENTATIVE_RESULTS,
    RESULTS,
    V3_BASELINE,
    evaluate,
    render_markdown,
    v3_evidence,
    v3_regression,
)


def _stable(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def _without_observed_runtime(result: dict[str, Any]) -> dict[str, Any]:
    cloned = json.loads(json.dumps(result))
    runtime = cloned.get("runtime")
    if isinstance(runtime, dict):
        runtime.pop("elapsed_wall_seconds", None)
    return cloned


def _difference_paths(expected: Any, actual: Any, prefix: str = "result") -> list[str]:
    if type(expected) is not type(actual):
        return [prefix]
    if isinstance(expected, dict):
        paths: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            if key not in expected or key not in actual:
                paths.append(f"{prefix}.{key}")
            else:
                paths.extend(_difference_paths(expected[key], actual[key], f"{prefix}.{key}"))
        return paths
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [prefix]
        paths = []
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            paths.extend(_difference_paths(left, right, f"{prefix}[{index}]"))
        return paths
    return [] if expected == actual else [prefix]


def _failed_checks(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for group in ("gates", "comparative_checks"):
        for name, passed in result.get(group, {}).items():
            if not passed:
                failures.append(f"{group}.{name}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic map-codebase utility benchmarks.")
    parser.add_argument("--profile", choices=("representative", "full"), default="representative")
    parser.add_argument("--no-cache", action="store_true", help="diagnostic: rebuild every task state")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--output", type=Path)
    action.add_argument("--write", action="store_true")
    action.add_argument("--freeze-v3", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.profile, cache_enabled=not args.no_cache)
    rendered = _stable(result)
    results_path = RESULTS if args.profile == "full" else REPRESENTATIVE_RESULTS
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
        return 0
    if args.write:
        if not result["all_checks_pass"]:
            print(
                "Refusing to write failing benchmark evidence: " + ", ".join(_failed_checks(result)),
                file=sys.stderr,
            )
            return 1
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(rendered, encoding="utf-8")
        if args.profile == "full":
            REPORT.write_text(render_markdown(result), encoding="utf-8")
            print(f"Wrote {results_path.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}.")
        else:
            print(f"Wrote {results_path.relative_to(ROOT)}.")
        return 0
    if args.freeze_v3:
        if args.profile != "full":
            parser.error("--freeze-v3 requires --profile full")
        if not result["all_checks_pass"]:
            failed = _failed_checks(result)
            print("Refusing to freeze failing v3 evidence: " + ", ".join(failed), file=sys.stderr)
            return 1
        # A calibration is a single authoritative cold run.  Keep the raw
        # result, rendered report, and hash-bound v2 evidence in lockstep so
        # a later check cannot accidentally compare a baseline to a different
        # corpus execution.
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        RESULTS.write_text(rendered, encoding="utf-8")
        REPORT.write_text(render_markdown(result), encoding="utf-8")
        V3_BASELINE.write_text(_stable(v3_evidence(result)), encoding="utf-8")
        print(
            "Wrote "
            + ", ".join(
                str(path.relative_to(ROOT)) for path in (RESULTS, REPORT, V3_BASELINE)
            )
            + "."
        )
        return 0
    expected_results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.is_file() else {}
    report_is_stale = (
        args.profile == "full"
        and (
            not REPORT.is_file()
            or REPORT.read_text(encoding="utf-8") != render_markdown(result)
        )
    )
    runtime_failures: list[str] = []
    if expected_results:
        recorded = float(expected_results.get("runtime", {}).get("elapsed_wall_seconds", 0))
        floor = float(result["runtime"]["fixed_floor_seconds"])
        elapsed = float(result["runtime"]["elapsed_wall_seconds"])
        if not recorded or elapsed > max(2 * recorded, floor):
            runtime_failures.append(
                f"runtime {elapsed:.3f}s exceeds ceiling {max(2 * recorded, floor):.3f}s"
            )
    stable_expected = _without_observed_runtime(expected_results)
    stable_actual = _without_observed_runtime(result)
    if stable_expected != stable_actual or report_is_stale:
        differences = _difference_paths(stable_expected, stable_actual)[:20]
        detail = ", ".join(differences) if differences else "rendered report"
        print(f"Benchmark results are stale at: {detail}; run with --write.", file=sys.stderr)
        return 1
    regression = v3_regression(result) if args.profile == "full" else []
    if not result["all_checks_pass"] or regression or runtime_failures:
        failed = _failed_checks(result)
        print("Benchmark checks failed: " + ", ".join([*failed, *regression, *runtime_failures]), file=sys.stderr)
        return 1
    print("Benchmark results and gates are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
