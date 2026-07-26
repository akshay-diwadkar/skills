"""Copy or check the canonical plan-contract runtime in standalone skill packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "plan_contract_runtime.py"
TARGETS = (
    ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py",
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_runtime.py",
    ROOT / "skills" / "engineering" / "scope-issue" / "scripts" / "plan_runtime.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = SOURCE.read_bytes()
    stale = [target for target in TARGETS if not target.is_file() or target.read_bytes() != source]
    if args.check:
        for target in stale:
            print(f"Generated plan runtime is stale: {target.relative_to(ROOT)}", file=sys.stderr)
        return int(bool(stale))
    for target in TARGETS:
        target.write_bytes(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
