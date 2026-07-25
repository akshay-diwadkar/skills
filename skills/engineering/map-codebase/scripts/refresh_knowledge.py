#!/usr/bin/env python3
"""Incremental refresh and cheap freshness validation engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure skill scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from knowledge.freshness import check_freshness, refresh_knowledge

__all__ = ["check_freshness", "refresh_knowledge"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh codebase knowledge incrementally.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--changed-file", action="append", default=[], help="Explicitly changed file path")
    parser.add_argument("--output", help="Output directory")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    k_dir = Path(args.output).resolve() if args.output else None

    res = refresh_knowledge(repo_root, args.changed_file, k_dir)
    print(f"Refresh completed ({res['mode']} mode): status={res['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
