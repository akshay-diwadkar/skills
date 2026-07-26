#!/usr/bin/env python3
"""Validate a strict v5 plan against its target repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plan_inventory import load_inventory, unresolved_candidates
from plan_runtime import validate_plan


def collect_diagnostics(
    text: str, tier: str, repo_root: Path, *, require_finalized: bool = False, baseline: dict | None = None,
    inventory: dict | None = None,
):
    plan, diagnostics = validate_plan(text, repo_root, require_finalized=require_finalized, baseline=baseline)
    if plan and tier != plan.tier:
        from plan_runtime import Diagnostic

        diagnostics.append(
            Diagnostic("tier.cli_mismatch", f"CLI tier {tier} does not match final metadata tier {plan.tier}.")
        )
    if plan and inventory is not None:
        from plan_runtime import Diagnostic

        diagnostics.extend(
            Diagnostic("inventory.unresolved", f"Inventory candidate is not reconciled: {candidate}")
            for candidate in unresolved_candidates(plan, inventory)
        )
    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("tiny", "standard", "high-risk"), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--require-finalized", action="store_true")
    parser.add_argument("--baseline", type=Path, required=True, help="Planning snapshot JSON captured before exploration.")
    parser.add_argument("--inventory", type=Path, required=True, help="Inventory JSON created by prepare_plan.py.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    text = Path(args.path).read_text(encoding="utf-8") if args.path else __import__("sys").stdin.read()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        inventory = load_inventory(args.inventory.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(f"--baseline and --inventory must be readable valid JSON: {exc}")
    diagnostics = collect_diagnostics(
        text, args.tier, args.repo_root.resolve(), require_finalized=args.require_finalized, baseline=baseline, inventory=inventory
    )
    if args.format == "json":
        print(
            json.dumps(
                {"valid": not diagnostics, "contract_version": 5, "diagnostics": [x.to_dict() for x in diagnostics]},
                indent=2,
            )
        )
    else:
        for item in diagnostics:
            print(item)
        if not diagnostics:
            print("Plan validation passed.")
    return int(bool(diagnostics))


if __name__ == "__main__":
    raise SystemExit(main())
