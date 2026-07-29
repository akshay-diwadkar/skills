#!/usr/bin/env python3
"""Attach a review-only unified diff to one implementation change row."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from implementation_contract import unified_diff_for_change


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--change-index", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        bundle: dict[str, Any] = json.loads(args.bundle.read_text(encoding="utf-8"))
        changes = bundle["changes"]
        if not isinstance(changes, list):
            raise ValueError("bundle changes must be a list")
        change = changes[args.change_index]
        if not isinstance(change, dict):
            raise ValueError("selected change must be an object")
        change["unified_diff"] = unified_diff_for_change(
            args.repo_root.resolve(), args.bundle.resolve(), change
        )
        args.bundle.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    except (IndexError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
