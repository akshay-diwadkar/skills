#!/usr/bin/env python3
"""Run shape and rubric checks on a plan draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import _plan_utils, check_plan_shape, check_plan_rubric
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_plan_rubric
import check_plan_shape
from _plan_utils import Diagnostic, read_plan, validate_receipt
from plan_model import coverage_summary, validate_semantics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=("tiny", "standard", "high-risk"),
        required=True,
        help="Plan complexity tier to validate against.",
    )
    parser.add_argument(
        "--require-finalized",
        action="store_true",
        help="Require a valid v3 validation receipt matching the plan body.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Plan markdown file. Reads stdin when omitted or set to '-'.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--warn",
        action="store_true",
        help="Separate warnings from errors. If set, warnings do not cause exit code 1.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Resolve file:line citations against this repository root.",
    )
    return parser.parse_args()


def collect_diagnostics(text: str, tier: str, repo_root: Path, *, require_finalized: bool = False) -> list[Diagnostic]:
    shape_diags = check_plan_shape.validate(text, tier)
    rubric_diags = check_plan_rubric.validate(text, tier)
    semantic_diags = validate_semantics(text, tier, repo_root)
    receipt_diags = validate_receipt(text, required=require_finalized)
    all_diags = shape_diags + rubric_diags + semantic_diags + receipt_diags

    # Deduplicate diagnostics by code and line
    seen = set()
    deduped_diags: list[Diagnostic] = []
    for diag in all_diags:
        key = (diag.code, diag.line, diag.message)
        if key not in seen:
            seen.add(key)
            deduped_diags.append(diag)

    return deduped_diags


def main() -> int:
    args = parse_args()
    try:
        text = read_plan(args.path)
    except Exception as e:
        print(f"Error reading plan: {e}", file=sys.stderr)
        return 1

    repo_root = (args.repo_root or Path.cwd()).resolve()
    deduped_diags = collect_diagnostics(
        text,
        args.tier,
        repo_root,
        require_finalized=args.require_finalized,
    )
    errors = [d for d in deduped_diags if not d.is_warning]
    warnings = [d for d in deduped_diags if d.is_warning]

    if args.format == "json":
        output = {
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "passed": len(errors) == 0 and (args.warn or len(warnings) == 0),
            "contract_version": 3,
            "coverage": coverage_summary(text, repo_root),
        }
        print(json.dumps(output, indent=2))
    else:
        if deduped_diags:
            print(f"Plan validation findings ({args.tier} tier):")
            for d in deduped_diags:
                print(f"- {d}")
        else:
            print("Plan validation passed.")

    if errors:
        return 1
    if warnings and not args.warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
