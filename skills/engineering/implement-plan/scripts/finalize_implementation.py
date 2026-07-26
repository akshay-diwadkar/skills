#!/usr/bin/env python3
"""Validate an implementation bundle; v5 plans carry their own receipt."""

from __future__ import annotations

import argparse
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
    diagnostics = validate_bundle(bundle, args.plan.read_text(encoding="utf-8"), args.repo_root)
    if diagnostics:
        for item in diagnostics:
            print(item)
        return 1
    print(json.dumps(bundle, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
