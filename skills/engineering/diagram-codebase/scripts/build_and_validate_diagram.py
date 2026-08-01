#!/usr/bin/env python3
"""Build and validate an approved diagram payload in one runtime command."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from build_diagram import build_diagram


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fidelity", required=True)
    parser.add_argument("--create-dirs", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        build_diagram(args.data, args.output, args.overwrite, args.create_dirs, args.fidelity)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    validator = Path(__file__).with_name("validate_diagram.py")
    return subprocess.run([sys.executable, str(validator), str(args.output)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
