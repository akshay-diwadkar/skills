#!/usr/bin/env python3
"""Validate a v3 plan and emit the only submission-ready, receipt-stamped form."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _plan_utils import VALIDATION_RECEIPT_RE, finalize_plan_text, read_plan, receipt_lines
from check_plan import collect_diagnostics
from plan_contract import load_contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(load_contract()["tiers"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("path", nargs="?", help="Draft Markdown path; read stdin when omitted or '-'.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        draft = read_plan(args.path)
    except Exception as exc:
        print(f"Error reading plan: {exc}", file=sys.stderr)
        return 1

    receipts = receipt_lines(draft)
    if len(receipts) > 1:
        print("Error [finalization.receipt.duplicate]: Draft contains multiple validation receipts", file=sys.stderr)
        return 1
    if receipts and VALIDATION_RECEIPT_RE.fullmatch(receipts[0][1]) is None:
        print("Error [finalization.receipt.malformed]: Draft contains a malformed validation receipt", file=sys.stderr)
        return 1

    diagnostics = collect_diagnostics(
        draft,
        args.tier,
        args.repo_root.resolve(),
        require_finalized=False,
    )
    if diagnostics:
        print(f"Plan finalization blocked ({args.tier} tier):", file=sys.stderr)
        for item in diagnostics:
            print(f"- {item}", file=sys.stderr)
        return 1

    finalized = finalize_plan_text(draft)
    receipt_diagnostics = collect_diagnostics(
        finalized,
        args.tier,
        args.repo_root.resolve(),
        require_finalized=True,
    )
    if receipt_diagnostics:
        print("Plan finalization produced an invalid result:", file=sys.stderr)
        for item in receipt_diagnostics:
            print(f"- {item}", file=sys.stderr)
        return 1
    sys.stdout.write(finalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
