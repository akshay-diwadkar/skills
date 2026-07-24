#!/usr/bin/env python3
"""Print a design-assessment scaffold for one L0-L3 level."""

from __future__ import annotations

import argparse

from assessment_contract import load_contract, render_scaffold


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=tuple(load_contract()["levels"]), required=True)
    parser.add_argument("--mode", choices=("targeted", "autonomous-discovery", "discovery-only"), default="targeted")
    args = parser.parse_args()
    print(render_scaffold(args.level, mode=args.mode), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
