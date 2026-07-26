#!/usr/bin/env python3
"""Print plan-contract v5 hashes for an exact inclusive source excerpt."""

from __future__ import annotations

import argparse
from pathlib import Path

from plan_runtime import _hash


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--start-line", type=int, required=True)
    parser.add_argument("--end-line", type=int, required=True)
    args = parser.parse_args()

    if not args.path.is_file():
        parser.error(f"--path must be an existing file: {args.path}")

    source = args.path.read_text(encoding="utf-8", errors="replace").splitlines()
    if args.start_line < 1 or args.end_line < args.start_line or args.end_line > len(source):
        parser.error(
            "--start-line and --end-line must form an inclusive range within "
            f"1-{len(source)}"
        )

    excerpt = "\n".join(source[args.start_line - 1 : args.end_line]) + "\n"
    print(f"excerpt-sha256: {_hash(excerpt.encode())}")
    print(f"file-sha256: {_hash(args.path.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
