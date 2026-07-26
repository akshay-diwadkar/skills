#!/usr/bin/env python3
"""Generate portable Python contract data from the sole editable JSON contract."""

from __future__ import annotations

import argparse
import json
import pprint
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skills" / "engineering" / "plan-change" / "references" / "plan-contract.json"
TARGETS = (
    ROOT / "tools" / "plan_contract_data.py",
    ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_contract_data.py",
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_contract_data.py",
    ROOT / "skills" / "engineering" / "scope-issue" / "scripts" / "plan_contract_data.py",
)


def load_contract() -> dict[str, Any]:
    value = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("contract_version") != 5:
        raise ValueError("plan-contract.json must be a version 5 JSON object")
    return value


def rendered_module(contract: dict[str, Any]) -> str:
    literal = pprint.pformat(contract, width=120, sort_dicts=False)
    return (
        '"""Generated from references/plan-contract.json; do not edit."""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        f"CONTRACT: dict[str, Any] = {literal}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = rendered_module(load_contract())
    stale = [target for target in TARGETS if not target.is_file() or target.read_text(encoding="utf-8") != expected]
    if args.check:
        for target in stale:
            print(f"Generated plan contract data is stale: {target.relative_to(ROOT)}", file=sys.stderr)
        return int(bool(stale))
    for target in TARGETS:
        target.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
