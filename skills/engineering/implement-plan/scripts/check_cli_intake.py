#!/usr/bin/env python3
"""Block common-CLI runs whose planned targets were already dirty at intake."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _diagnostic(path: str) -> dict[str, Any]:
    return {
        "code": "bundle.dirty_target",
        "message": f"Planned target already had uncommitted changes at intake: {path}.",
        "hint": (
            "Preserve the target and use the direct compatibility workflow only after "
            "explicit user authorization."
        ),
        "path": path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for row in bundle.get("workspace", {}).get("targets", []):
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            targets.add(row["path"])
    dirty = bundle.get("workspace", {}).get("initial_dirty", {})
    dirty_targets = sorted(targets & set(dirty) if isinstance(dirty, dict) else set())
    diagnostics = [_diagnostic(path) for path in dirty_targets]
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": diagnostics}, indent=2))
    else:
        for item in diagnostics:
            print(f"Error [{item['code']}]: {item['message']} Fix: {item['hint']}")
    return int(bool(diagnostics))


if __name__ == "__main__":
    raise SystemExit(main())
