#!/usr/bin/env python3
"""Synchronize the standalone skill copies of the common CLI runtime."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "skill_protocol" / "runtime.py"
TARGETS = (
    ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "_skill_protocol_runtime.py",
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "_skill_protocol_runtime.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail instead of updating stale copies.")
    args = parser.parse_args()
    source = SOURCE.read_bytes()
    stale = [target for target in TARGETS if not target.is_file() or target.read_bytes() != source]
    if args.check:
        for target in stale:
            print(f"Stale common skill CLI runtime: {target.relative_to(ROOT)}", file=sys.stderr)
        return int(bool(stale))
    for target in stale:
        target.write_bytes(source)
        print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
