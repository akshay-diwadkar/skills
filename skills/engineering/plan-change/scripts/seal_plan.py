#!/usr/bin/env python3
"""Validate and seal one agent-authored plan-contract v6 draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from plan_runtime import Diagnostic, seal_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--handoff-item")
    parser.add_argument("--draft", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = seal_plan(args.repo_root, args.request_file, args.draft, handoff_item=args.handoff_item)
    except (OSError, UnicodeError, ValueError) as exc:
        diagnostics = getattr(exc, "diagnostics", None)
        if not diagnostics:
            diagnostics = (
                Diagnostic(
                    "record.invalid",
                    str(exc),
                    "Correct the named input file or draft and rerun the same seal command.",
                ),
            )
        print(json.dumps({"valid": False, "diagnostics": [item.to_dict(artifact=str(args.draft)) for item in diagnostics]}, sort_keys=True, separators=(",", ":")))
        return 1
    sys.stdout.write(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
