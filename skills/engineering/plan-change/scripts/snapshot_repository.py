#!/usr/bin/env python3
"""Write a planning-session repository snapshot outside the target repository."""

from __future__ import annotations

import argparse
from pathlib import Path

from plan_runtime import write_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.repo_root.resolve(), args.output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        parser.error("snapshot output must be outside the target repository")
    write_snapshot(root, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
