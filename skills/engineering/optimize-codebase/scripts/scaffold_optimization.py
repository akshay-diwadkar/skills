#!/usr/bin/env python3
"""Print a canonical optimization scaffold."""

from __future__ import annotations

import argparse

from optimization_contract import load_contract, render_scaffold


def main() -> int:
    contract = load_contract()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=tuple(contract["scopes"]), required=True)
    parser.add_argument("--stage", choices=tuple(contract["stages"]), required=True)
    args = parser.parse_args()
    print(render_scaffold(args.scope, args.stage), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
