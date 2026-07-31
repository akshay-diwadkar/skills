#!/usr/bin/env python3
"""Apply deterministic audit categories and severity to an audit bundle."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--severity", choices=("critical", "high", "medium", "low"), required=True)
    args = parser.parse_args()
    path = args.bundle.resolve(strict=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        parser.error("bundle must be a JSON object")
    context = payload.setdefault("audit_context", {})
    if not isinstance(context, dict):
        parser.error("audit_context must be a JSON object")
    context["categories"] = sorted(set(args.category))
    context["severity_threshold"] = args.severity
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
