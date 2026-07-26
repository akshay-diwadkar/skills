#!/usr/bin/env python3
"""Finalize a valid v5 plan with targeted repository binding."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from check_plan import collect_diagnostics
from plan_inventory import load_inventory
from plan_runtime import finalized_text, parse_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("tiny", "standard", "high-risk"), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--baseline", type=Path, required=True, help="Planning snapshot JSON captured before exploration."
    )
    parser.add_argument("--inventory", type=Path, required=True, help="Inventory JSON created by prepare_plan.py.")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        draft = Path(args.path).read_text(encoding="utf-8") if args.path else sys.stdin.read()
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        inventory = load_inventory(args.inventory.resolve())
        plan, diagnostics = parse_plan(draft)
        if diagnostics or plan is None:
            raise ValueError("\n".join(str(item) for item in diagnostics))
        if plan.tier != args.tier:
            raise ValueError(f"CLI tier {args.tier} does not match final metadata tier {plan.tier}.")
        diagnostics = collect_diagnostics(draft, args.tier, root, baseline=baseline, inventory=inventory)
        if diagnostics:
            raise ValueError("\n".join(str(item) for item in diagnostics))
        sys.stdout.write(finalized_text(draft, root, baseline=baseline))
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
