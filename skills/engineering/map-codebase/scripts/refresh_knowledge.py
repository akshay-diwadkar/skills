#!/usr/bin/env python3
"""Incremental refresh and cheap freshness validation engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure skill scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from finalize_knowledge import KnowledgeFinalizationError, refresh_and_finalize
from knowledge.freshness import check_freshness, refresh_knowledge

__all__ = ["check_freshness", "refresh_knowledge"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh codebase knowledge incrementally.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--changed-file", action="append", default=[], help="Explicitly changed file path")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    k_dir = Path(args.output) if args.output else None
    try:
        res = refresh_and_finalize(repo_root, args.changed_file, k_dir)
    except KnowledgeFinalizationError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(res, indent=2))
    else:
        print(f"Refresh completed ({res['mode']} mode): status={res['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
