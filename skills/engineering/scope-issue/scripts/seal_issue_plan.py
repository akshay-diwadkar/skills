#!/usr/bin/env python3
"""Atomically seal the sole selected-issue handoff artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from check_issue_plan import validate_plan


RECEIPT_RE = re.compile(r"^<!-- issue-handoff: 1; sha256: ([0-9a-f]{64}) -->$")


def _receipt_free(text: str) -> str:
    first, separator, body = text.partition("\n")
    match = RECEIPT_RE.fullmatch(first)
    if match is None:
        return text
    if not separator or hashlib.sha256(body.encode("utf-8")).hexdigest() != match.group(1):
        raise ValueError("issue handoff receipt does not match content")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--issue-json", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        text = _receipt_free(args.draft.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "diagnostics": [{"code": "handoff.invalid", "message": str(exc)}]}))
        return 1
    errors = validate_plan(args.draft, args.issue_json, args.repo_root)
    if errors:
        print(json.dumps({"valid": False, "diagnostics": [{"code": "issue-handoff.invalid", "message": item} for item in errors]}, sort_keys=True, separators=(",", ":")))
        return 1
    body = text.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sealed = f"<!-- issue-handoff: 1; sha256: {digest} -->\n{body}"
    destination = args.output_dir.resolve() / "issue-handoff.md"
    extras = [path for path in destination.parent.iterdir() if path != destination] if destination.parent.is_dir() else []
    if extras:
        print(json.dumps({"valid": False, "diagnostics": [{"code": "output.not_exclusive", "message": "output directory contains artifacts other than issue-handoff.md"}]}))
        return 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=destination.parent, delete=False) as temporary:
        temporary.write(sealed)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(json.dumps({"status": "sealed", "path": str(destination)}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
