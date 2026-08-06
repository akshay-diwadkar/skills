"""Copy or check versioned plan runtimes in standalone consumer skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V7_SOURCE = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py"
V7_TARGETS = (
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v7_runtime.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    pairs = [
        *((V7_SOURCE, target) for target in V7_TARGETS),
    ]
    stale = [target for source, target in pairs if not target.is_file() or target.read_bytes() != source.read_bytes()]
    if args.check:
        for target in stale:
            print(f"Generated plan runtime is stale: {target.relative_to(ROOT)}", file=sys.stderr)
        return int(bool(stale))
    for source, target in pairs:
        target.write_bytes(source.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
