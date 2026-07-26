#!/usr/bin/env python3
"""Validate an implementation bundle; v5 plans carry their own receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from check_implementation import validate_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict) or bundle.get("status") != "complete":
        print("Error [bundle.receipt_status]: Only a complete implementation bundle may receive a validation receipt.")
        return 1
    diagnostics = validate_bundle(bundle, args.plan.read_text(encoding="utf-8"), args.repo_root)
    if diagnostics:
        for item in diagnostics:
            print(item)
        return 1
    receipt_body = dict(bundle)
    receipt_body.pop("validation_receipt", None)
    bundle["validation_receipt"] = {
        "implementation_contract": 2,
        "plan_contract": 5,
        "sha256": hashlib.sha256(json.dumps(receipt_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(bundle, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
