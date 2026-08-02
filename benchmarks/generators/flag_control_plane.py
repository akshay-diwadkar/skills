"""Independently executable generator for the flag-control-plane fixture."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.generators.generate import generate_fixture  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    generate_fixture("flag-control-plane", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
