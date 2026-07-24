#!/usr/bin/env python3
"""Scaffold a design-codebase-with-senior-dev assessment artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_contract import render_scaffold  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a design assessment artifact.")
    parser.add_argument("--level", default="L0", choices=["L0", "L1", "L2", "L3", "discovery-only"], help="Assessment level.")
    parser.add_argument("--mode", default="targeted", choices=["targeted", "autonomous-discovery", "discovery-only"], help="Invocation mode.")
    args = parser.parse_args()

    mode = args.mode
    if args.level == "discovery-only" or mode == "discovery-only":
        mode = "discovery-only"
        level = "L0"
    else:
        level = args.level

    sys.stdout.write(render_scaffold(level, mode=mode))
    return 0


if __name__ == "__main__":
    sys.exit(main())
