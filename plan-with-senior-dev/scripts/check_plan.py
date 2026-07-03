#!/usr/bin/env python3
"""Run shape and rubric checks on a plan draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import _plan_utils, check_plan_shape, check_plan_rubric
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plan_utils import Diagnostic, read_plan
import check_plan_shape
import check_plan_rubric


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=("tiny", "standard", "high-risk"),
        required=True,
        help="Plan complexity tier to validate against.",
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
        "--issue-related",
        action="store_true",
        help="Require the Post-Resolution Audit Follow-Up section for issue or audit-finding plans.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        text = read_plan(args.path)
    except Exception as e:
        print(f"Error reading plan: {e}", file=sys.stderr)
        return 1

    # Run checks
    shape_diags = check_plan_shape.validate(text, args.tier)
    rubric_diags = check_plan_rubric.validate(text, args.tier, issue_related=args.issue_related)

    all_diags = shape_diags + rubric_diags

    # Deduplicate diagnostics by code and line
    seen = set()
    deduped_diags: list[Diagnostic] = []
    for diag in all_diags:
        key = (diag.code, diag.line, diag.message)
        if key not in seen:
            seen.add(key)
            deduped_diags.append(diag)

    errors = [d for d in deduped_diags if not d.is_warning]
    warnings = [d for d in deduped_diags if d.is_warning]

    if args.format == "json":
        output = {
            "errors": [e.to_dict() for e in errors],
            "warnings": [w.to_dict() for w in warnings],
            "passed": len(errors) == 0 and (args.warn or len(warnings) == 0),
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
