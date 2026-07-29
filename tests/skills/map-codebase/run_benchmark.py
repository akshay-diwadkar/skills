#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    evaluate,
    render_markdown,
)


def _stable(result: dict[str, object]) -> str:
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic map-codebase utility benchmarks.")
    parser.add_argument("--profile", choices=("representative", "full"), default="representative")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--output", type=Path)
    action.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.profile)
    rendered = _stable(result)
    results_path = RESULTS if args.profile == "full" else REPRESENTATIVE_RESULTS
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
        return 0
    if args.write:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(rendered, encoding="utf-8")
        if args.profile == "full":
            REPORT.write_text(render_markdown(result), encoding="utf-8")
            print(f"Wrote {results_path.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}.")
        else:
            print(f"Wrote {results_path.relative_to(ROOT)}.")
        return 0
    expected_results = results_path.read_text(encoding="utf-8") if results_path.is_file() else ""
    report_is_stale = (
        args.profile == "full"
        and (
            not REPORT.is_file()
            or REPORT.read_text(encoding="utf-8") != render_markdown(result)
        )
    )
    if expected_results != rendered or report_is_stale:
        print("Benchmark results are stale; run with --write.", file=sys.stderr)
        return 1
    if not result["all_gates_pass"]:
        failed = [name for name, passed in result["gates"].items() if not passed]
        print("Benchmark gates failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    print("Benchmark results and gates are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
