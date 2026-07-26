#!/usr/bin/env python3
"""Create an isolated v5 planning workspace with a baseline, inventory, and draft."""

from __future__ import annotations

import argparse
from pathlib import Path

from plan_contract import INTENTS, render_scaffold
from plan_inventory import build_inventory
from plan_runtime import TIERS, snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--request-file", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--tier", choices=TIERS, required=True)
    parser.add_argument("--intent", choices=INTENTS, required=True)
    parser.add_argument("--risk-domain", action="append", default=[])
    args = parser.parse_args()
    root = args.repo_root.resolve()
    request = args.request_file.resolve().read_text(encoding="utf-8")
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "baseline.json").write_text(__import__("json").dumps(snapshot(root), indent=2) + "\n", encoding="utf-8")
    inventory = build_inventory(root, request)
    (run_dir / "inventory.json").write_text(__import__("json").dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (run_dir / "draft.md").write_text(render_scaffold(args.tier, args.intent, args.risk_domain), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
