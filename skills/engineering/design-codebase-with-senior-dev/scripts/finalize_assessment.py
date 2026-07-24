#!/usr/bin/env python3
"""Validate a v2 design assessment and emit the only submission-ready, receipt-stamped form."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from assessment_contract import (
    VALIDATION_RECEIPT_RE,
    finalize_assessment_text,
    load_contract,
    receipt_lines,
)
from check_assessment import validate


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=tuple(load_contract()["levels"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("path", nargs="?", help="Draft Markdown path; read stdin when omitted or '-'.")
    return parser.parse_args(argv)


def read_assessment(path: str | None) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        draft = read_assessment(args.path)
    except Exception as exc:
        print(f"Error reading assessment: {exc}", file=sys.stderr)
        return 1

    receipts = receipt_lines(draft)
    if len(receipts) > 1:
        print("Error [finalization.receipt.duplicate]: Draft contains multiple validation receipts", file=sys.stderr)
        return 1
    if receipts and VALIDATION_RECEIPT_RE.fullmatch(receipts[0][1]) is None:
        print("Error [finalization.receipt.malformed]: Draft contains a malformed validation receipt", file=sys.stderr)
        return 1

    diagnostics = validate(
        draft,
        args.level,
        args.repo_root.resolve(),
        require_finalized=False,
    )
    if diagnostics:
        print(f"Assessment finalization blocked ({args.level} level):", file=sys.stderr)
        for item in diagnostics:
            print(f"- {item}", file=sys.stderr)
        return 1

    finalized = finalize_assessment_text(draft, args.level)
    receipt_diagnostics = validate(
        finalized,
        args.level,
        args.repo_root.resolve(),
        require_finalized=True,
    )
    if receipt_diagnostics:
        print("Assessment finalization produced an invalid result:", file=sys.stderr)
        for item in receipt_diagnostics:
            print(f"- {item}", file=sys.stderr)
        return 1

    sys.stdout.write(finalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
