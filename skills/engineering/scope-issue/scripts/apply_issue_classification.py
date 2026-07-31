#!/usr/bin/env python3
"""Apply a recorded deterministic issue classification to plan metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from _classification_runtime import verify_override

MARKER = re.compile(
    r"(<!--\s*issue-plan-metadata\s*-->\s*```json\s*)(\{.*?\})(\s*```)",
    re.DOTALL,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--override-file", type=Path)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        classification = json.loads(args.classification.resolve(strict=True).read_text(encoding="utf-8"))
        values = dict(classification["recommendation"]["values"])
        if args.override_file:
            values = verify_override(classification, args.override_file, args.repo_root)
        plan = args.plan.resolve(strict=True)
        text = plan.read_text(encoding="utf-8")
        match = MARKER.search(text)
        if not match:
            raise ValueError("issue plan metadata marker is missing")
        metadata = json.loads(match.group(2))
        metadata["status"] = values["status"]
        routing = metadata.setdefault("routing", {})
        routing["senior_required"] = values["senior_required"]
        routing["reasons"] = values["routing_reasons"]
        routing["task_types"] = values["task_types"]
        routing["tier"] = values["tier"]
        replacement = match.group(1) + json.dumps(metadata, sort_keys=True, separators=(",", ":")) + match.group(3)
        updated = text[:match.start()] + replacement + text[match.end():]
        handle, temporary = tempfile.mkstemp(prefix=f".{plan.name}.", suffix=".tmp", dir=plan.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(updated)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, plan)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"issue classification apply failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
