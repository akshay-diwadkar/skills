#!/usr/bin/env python3
"""Validate a plan-ready design handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from handoff_contract import validate_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--verify-evidence",
        action="store_true",
        help="Require and verify sha256 bindings for every local evidence record.",
    )
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()

    if not args.repo_root.is_absolute() or not args.repo_root.is_dir():
        parser.error("--repo-root must be an absolute repository directory")
    if not args.draft.is_file():
        parser.error("draft must be a Markdown file")

    _handoff, diagnostics = validate_handoff(
        args.draft.read_text(encoding="utf-8"),
        args.repo_root,
        require_evidence_hashes=args.verify_evidence,
    )
    if args.format == "json":
        print(json.dumps([diagnostic.as_dict() for diagnostic in diagnostics], indent=2))
    else:
        stream = sys.stderr if diagnostics else sys.stdout
        if diagnostics:
            for diagnostic in diagnostics:
                print(diagnostic, file=stream)
        else:
            print("Design handoff is valid.", file=stream)
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
