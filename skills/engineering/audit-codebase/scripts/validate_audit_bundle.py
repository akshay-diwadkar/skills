#!/usr/bin/env python3
"""Validate a audit-codebase bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _diagnostic_contract import normalize_diagnostic
from audit_bundle import AuditBundleError, read_json, validate_audit_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a codebase audit bundle.")
    parser.add_argument("input", help="Path to the audit bundle JSON.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    try:
        raw = read_json(Path(args.input))
    except AuditBundleError as exc:
        if args.format == "json":
            item = normalize_diagnostic(
                {"code": "audit.input.invalid", "message": str(exc)},
                skill="audit-codebase",
                phase="validate",
                artifact="audit-bundle",
                path=args.input,
                next_command={
                    "argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
                    "cwd": str(Path.cwd()),
                },
            )
            print(json.dumps({"valid": False, "diagnostics": [item]}, sort_keys=True, separators=(",", ":")))
            return 2
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_audit_bundle(raw)
    if errors:
        if args.format == "json":
            retry = {
                "argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
                "cwd": str(Path.cwd()),
            }
            diagnostics = [
                normalize_diagnostic(
                    {"code": "audit.bundle.invalid", "message": error},
                    skill="audit-codebase",
                    phase="validate",
                    artifact="audit-bundle",
                    path=args.input,
                    next_command=retry,
                )
                for error in errors
            ]
            print(
                json.dumps(
                    {"valid": False, "diagnostics": diagnostics},
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 2
        print("Audit bundle validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        print('{"diagnostics":[],"valid":true}')
    else:
        print("Audit bundle is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
