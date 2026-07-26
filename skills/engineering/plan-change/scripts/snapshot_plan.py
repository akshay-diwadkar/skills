#!/usr/bin/env python3
"""Capture a planning-only repository baseline before exploration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plan_runtime import snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(snapshot(args.repo_root.resolve()), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
