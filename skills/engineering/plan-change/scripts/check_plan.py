#!/usr/bin/env python3
"""Validate a v4 plan against its typed contract and target repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _plan_utils import read_plan
from plan_contract import load_contract
from plan_runtime import load_snapshot
from v4_model import validate


def collect_diagnostics(
    text: str, tier: str, repo_root: Path, *, require_finalized: bool = False, baseline: dict | None = None
):
    return validate(text, repo_root, tier, require_finalized=require_finalized, baseline=baseline)


def main() -> int:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(contract["tiers"]), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--require-finalized", action="store_true")
    parser.add_argument("--initial-state", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    text = read_plan(args.path)
    baseline = load_snapshot(args.initial_state) if args.initial_state else None
    diagnostics = collect_diagnostics(
        text, args.tier, args.repo_root.resolve(), require_finalized=args.require_finalized, baseline=baseline
    )
    if args.format == "json":
        print(
            json.dumps(
                {
                    "valid": not diagnostics,
                    "contract_version": 4,
                    "diagnostics": [item.to_dict() for item in diagnostics],
                },
                indent=2,
            )
        )
    elif diagnostics:
        for item in diagnostics:
            print(item)
    else:
        print("Plan validation passed.")
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
