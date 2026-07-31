#!/usr/bin/env python3
"""Block common-CLI runs whose planned targets were already dirty at intake."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _diagnostic_contract import normalize_diagnostic


def _diagnostic(path: str, bundle: Path | None = None) -> dict[str, Any]:
    message = f"Planned target already had uncommitted changes at intake: {path}."
    hint = (
        "Preserve the target and use the direct compatibility workflow only after "
        "explicit user authorization."
    )
    return normalize_diagnostic(
        {
            "code": "bundle.dirty_target",
            "category": "unsafe_state",
            "message": message,
            "hint": hint,
            "record": path,
            "field": "initial_dirty",
            "supporting_evidence": [message],
            "required_action": "Restore the planned target to its recorded clean intake state, then restart the run.",
            "valid_repairs": [
                "Preserve the existing work outside this run and restore the target to a clean intake state.",
                "Finish and record the existing work before starting a new implementation run.",
            ],
        },
        skill="implement-plan",
        phase="start",
        artifact="implementation-bundle",
        path=bundle or "implementation.json",
        next_command=None,
    )


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
    retry = {"argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], "cwd": str(Path.cwd())}
    diagnostics = [_diagnostic(path, args.bundle) for path in dirty_targets]
    for item in diagnostics:
        item["next_command"] = retry
    if args.format == "json":
        print(json.dumps({"valid": not diagnostics, "diagnostics": diagnostics}, sort_keys=True, separators=(",", ":")))
    else:
        for item in diagnostics:
            print(f"Error [{item['code']}]: {item['message']} Fix: {item['hint']}")
    return int(bool(diagnostics))


if __name__ == "__main__":
    raise SystemExit(main())
