#!/usr/bin/env python3
"""Validate an implementation-contract v3 bundle and stamp its receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from check_implementation import validate_bundle
from implementation_contract import plan_contract_version


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
    plan_text = args.plan.read_text(encoding="utf-8")
    diagnostics = validate_bundle(bundle, plan_text, args.repo_root)
    if diagnostics:
        for item in diagnostics:
            print(item)
        return 1
    receipt_body = dict(bundle)
    receipt_body.pop("validation_receipt", None)
    bundle["validation_receipt"] = {
        "implementation_contract": 3,
        "plan_contract": plan_contract_version(plan_text),
        "sha256": hashlib.sha256(json.dumps(receipt_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(bundle, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
