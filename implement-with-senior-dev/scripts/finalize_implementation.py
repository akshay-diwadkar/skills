#!/usr/bin/env python3
"""Validate and stamp a canonical validation receipt into an implementation-run bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _plan_utils import bundle_digest
from check_implementation import validate_bundle


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("bundle", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        bundle_text = args.bundle.read_text(encoding="utf-8")
        bundle = json.loads(bundle_text)
        plan_text = args.plan.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Error reading inputs: {exc}\n")
        return 1

    # Remove any existing validation receipt before running checks
    bundle.pop("validation_receipt", None)

    diagnostics = validate_bundle(bundle, plan_text, args.repo_root.resolve(), require_receipt=False)
    if diagnostics:
        sys.stderr.write("Implementation finalization failed:\n")
        for item in diagnostics:
            sys.stderr.write(f"- {item}\n")
        return 1

    # Compute digest and stamp receipt
    digest = bundle_digest(bundle)
    bundle["validation_receipt"] = {
        "version": 1,
        "sha256": digest,
    }

    # Write stamped bundle back to disk
    canonical_text = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    args.bundle.write_text(canonical_text, encoding="utf-8")

    print(f"Implementation finalized and verified successfully. Receipt sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
