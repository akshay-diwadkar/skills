#!/usr/bin/env python3
"""Validate and receipt an optimization report selected by the agent."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from check_optimization import validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--path", choices=("fast", "full"), required=True)
    parser.add_argument("--scope", choices=("targeted", "sweep"), required=True)
    parser.add_argument("--stage", choices=("plan", "implementation"), required=True)
    args = parser.parse_args()
    text = args.report.read_text(encoding="utf-8")
    diagnostics = validate(text, args.path, args.scope, args.stage, args.repo_root)
    if diagnostics:
        print("\n".join(str(item) for item in diagnostics))
        return 1
    receipt = f"\n<!-- optimization-receipt: sha256:{hashlib.sha256(text.encode()).hexdigest()} -->\n"
    if "<!-- optimization-receipt:" not in text:
        args.report.write_text(text.rstrip() + receipt, encoding="utf-8")
    print('{"status":"sealed"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
