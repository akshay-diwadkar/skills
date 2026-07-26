#!/usr/bin/env python3
"""Finalize a valid v5 plan with targeted repository binding."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from plan_runtime import finalized_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("tiny", "standard", "high-risk"), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--initial-state", type=Path)
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    try:
        sys.stdout.write(
            finalized_text(
                Path(args.path).read_text(encoding="utf-8") if args.path else sys.stdin.read(), args.repo_root.resolve()
            )
        )
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
