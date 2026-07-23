#!/usr/bin/env python3
"""Validate a codebase-issue-auditor bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from audit_bundle import AuditBundleError, read_json, validate_audit_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a codebase audit bundle.")
    parser.add_argument("input", help="Path to the audit bundle JSON.")
    args = parser.parse_args(argv)

    try:
        raw = read_json(Path(args.input))
    except AuditBundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_audit_bundle(raw)
    if errors:
        print("Audit bundle validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    print("Audit bundle is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
