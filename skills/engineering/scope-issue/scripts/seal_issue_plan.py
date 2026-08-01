#!/usr/bin/env python3
"""Seal a selected-issue plan using only its supplied issue and evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

from check_issue_plan import validate_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--issue-json", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    errors = validate_plan(args.plan, args.issue_json, args.repo_root)
    if errors:
        print("\n".join(errors))
        return 1
    text = args.plan.read_text(encoding="utf-8")
    if "<!-- issue-plan-receipt:" not in text:
        sealed = text.rstrip() + f"\n<!-- issue-plan-receipt: sha256:{hashlib.sha256(text.encode()).hexdigest()} -->\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.plan.parent, delete=False) as temporary:
            temporary.write(sealed)
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, args.plan)
        finally:
            temporary_path.unlink(missing_ok=True)
    print('{"status":"sealed"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
