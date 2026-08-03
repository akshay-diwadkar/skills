#!/usr/bin/env python3
"""Validate and atomically seal the sole optimization handoff artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from check_optimization import validate


RECEIPT_RE = re.compile(r"^<!-- optimization-handoff: 1; sha256: ([0-9a-f]{64}) -->$")


def _receipt_free(text: str) -> str:
    first, separator, body = text.partition("\n")
    match = RECEIPT_RE.fullmatch(first)
    if match is None:
        return text
    if not separator or hashlib.sha256(body.encode("utf-8")).hexdigest() != match.group(1):
        raise ValueError("optimization handoff receipt does not match content")
    return body


def _write_atomic(destination: Path, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=destination.parent, delete=False) as temporary:
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scope", choices=("targeted", "sweep"), required=True)
    args = parser.parse_args()
    try:
        text = _receipt_free(args.draft.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "diagnostics": [{"code": "handoff.invalid", "message": str(exc)}]}))
        return 1
    diagnostics = validate(text, "full", args.scope, "plan", args.repo_root)
    if diagnostics:
        print(json.dumps({"valid": False, "diagnostics": [item.to_dict(path=args.draft) for item in diagnostics]}, sort_keys=True, separators=(",", ":")))
        return 1
    body = text.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    destination = args.output_dir.resolve() / "optimization-handoff.md"
    extras = [path for path in destination.parent.iterdir() if path != destination] if destination.parent.is_dir() else []
    if extras:
        print(json.dumps({"valid": False, "diagnostics": [{"code": "output.not_exclusive", "message": "output directory contains artifacts other than optimization-handoff.md"}]}))
        return 1
    _write_atomic(destination, f"<!-- optimization-handoff: 1; sha256: {digest} -->\n{body}")
    print(json.dumps({"status": "sealed", "path": str(destination)}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
