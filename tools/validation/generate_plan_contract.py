#!/usr/bin/env python3
"""Keep the deprecated v5 contract data in standalone consumer skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "plan_contract_data.py"
TARGETS = (
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_contract_data.py",
    ROOT / "skills" / "engineering" / "scope-issue" / "scripts" / "plan_contract_data.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = SOURCE.read_text(encoding="utf-8")
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
