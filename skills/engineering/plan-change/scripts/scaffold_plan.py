#!/usr/bin/env python3
from __future__ import annotations

import argparse

from plan_contract import load_contract, render_scaffold


def main() -> int:
    contract = load_contract()
    parser = argparse.ArgumentParser(description="Render a v5 plan scaffold.")
    parser.add_argument("--tier", choices=tuple(contract["tiers"]), required=True)
    parser.add_argument("--intent", choices=tuple(contract["intents"]), required=True)
    parser.add_argument("--risk-domain", action="append", default=[])
    args = parser.parse_args()
    try:
        print(render_scaffold(args.tier, args.intent, args.risk_domain), end="")
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
