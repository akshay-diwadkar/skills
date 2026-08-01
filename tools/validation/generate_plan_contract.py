#!/usr/bin/env python3
"""Retired v5 contract generator retained as a no-op compatibility check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS: tuple[Path, ...] = ()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale: list[Path] = []
    if args.check:
        for target in stale:
            print(f"Generated plan contract data is stale: {target.relative_to(ROOT)}", file=sys.stderr)
        return int(bool(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
