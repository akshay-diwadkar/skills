#!/usr/bin/env python3
"""Finalize a design-codebase-with-senior-dev assessment artifact by stamping a SHA-256 validation receipt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_contract import (  # noqa: E402
    finalize_assessment_text,
    receipt_lines,
)
from check_assessment import parse_assessment, validate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a design assessment with a SHA-256 validation receipt.")
    parser.add_argument("assessment_file", nargs="?", help="Path to draft assessment markdown file (reads stdin if omitted).")
    parser.add_argument("--level", required=False, help="Assessment level (L0, L1, L2, L3, discovery-only).")
    parser.add_argument("--mode", default="targeted", choices=["targeted", "autonomous-discovery", "discovery-only"], help="Invocation mode.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    args = parser.parse_args()

    if args.assessment_file and args.assessment_file != "-":
        path = Path(args.assessment_file)
        if not path.is_file():
            print(f"Error: Assessment file '{args.assessment_file}' not found.", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    if not text or not text.strip():
        print("Error: Empty assessment input.", file=sys.stderr)
        return 1

    rcpt_count = len(receipt_lines(text))
    if rcpt_count > 1:
        print("Error: Input contains multiple validation receipts.", file=sys.stderr)
        return 1

    assessment, parse_diags = parse_assessment(text)
    if parse_diags:
        for diag in parse_diags:
            print(f"Draft Diagnostic: {diag}", file=sys.stderr)

    effective_level = args.level or assessment.level
    effective_mode = args.mode if args.mode != "targeted" else assessment.mode

    if effective_mode == "discovery-only" or effective_level == "discovery-only":
        effective_mode = "discovery-only"
        effective_level = "discovery-only"

    # Validate draft before finalization
    draft_diagnostics = validate(text, effective_level if effective_level != "discovery-only" else "L0", Path(args.repo_root))
    draft_errors = [d for d in draft_diagnostics if not d.is_warning]
    if draft_errors:
        print("Error: Cannot finalize invalid assessment draft:", file=sys.stderr)
        for diag in draft_errors:
            print(f"  - {diag}", file=sys.stderr)
        return 1

    # Produce finalized text with stamped validation receipt
    finalized_text = finalize_assessment_text(text, effective_level if effective_level != "discovery-only" else "L0", mode=effective_mode)

    # Re-validate finalized text with --require-finalized
    final_diagnostics = validate(
        finalized_text,
        effective_level if effective_level != "discovery-only" else "L0",
        Path(args.repo_root),
        require_finalized=True,
    )
    final_errors = [d for d in final_diagnostics if not d.is_warning]
    if final_errors:
        print("Error: Finalized output failed validation:", file=sys.stderr)
        for diag in final_errors:
            print(f"  - {diag}", file=sys.stderr)
        return 1

    # Write ONLY the finalized assessment to stdout
    sys.stdout.write(finalized_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
