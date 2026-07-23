#!/usr/bin/env python3
"""Print a v3 plan scaffold for a tier and task type."""

from __future__ import annotations

import argparse

from plan_contract import load_contract, render_scaffold


def parse_args() -> argparse.Namespace:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(contract["tiers"]), required=True)
    parser.add_argument("--task-type", choices=tuple(contract["task_types"]), required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(render_scaffold(args.tier, args.task_type), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
