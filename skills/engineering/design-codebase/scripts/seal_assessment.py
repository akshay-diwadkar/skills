#!/usr/bin/env python3
"""Validate and atomically seal the sole design-codebase handoff artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from handoff_contract import seal_handoff


RECEIPT_RE = re.compile(r"^<!-- design-handoff: 1; sha256: ([0-9a-f]{64}) -->$")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("draft", type=Path)
    return parser


def _retry_command() -> dict[str, Any]:
    return {
        "argv": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "cwd": str(Path.cwd()),
    }


def _write_atomic(destination: Path, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _receipt_free(text: str) -> str:
    first, separator, body = text.partition("\n")
    match = RECEIPT_RE.fullmatch(first)
    if match is None:
        return text
    if not separator or hashlib.sha256(body.encode("utf-8")).hexdigest() != match.group(1):
        raise ValueError("design handoff receipt does not match content")
    return body


def _with_receipt(body: str) -> str:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"<!-- design-handoff: 1; sha256: {digest} -->\n{body}"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if not args.repo_root.is_absolute() or not args.repo_root.is_dir():
        parser.error("--repo-root must be an absolute repository directory")
    if not args.output_dir.is_absolute():
        parser.error("--output-dir must be absolute")
    if not args.draft.is_file():
        parser.error("draft must be a Markdown file")

    try:
        draft = _receipt_free(args.draft.read_text(encoding="utf-8"))
    except ValueError as exc:
        if args.format == "json":
            print(json.dumps({"valid": False, "diagnostics": [{"code": "receipt.invalid", "message": str(exc)}]}))
        else:
            print(str(exc), file=sys.stderr)
        return 1
    parsed, diagnostics, final_text = seal_handoff(draft, args.repo_root)
    del parsed
    if diagnostics:
        if args.format == "json":
            print(
                json.dumps(
                    [diagnostic.as_dict(path=args.draft, next_command=_retry_command()) for diagnostic in diagnostics],
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        else:
            print("Cannot seal invalid design handoff:", file=sys.stderr)
            for diagnostic in diagnostics:
                print(f"  - {diagnostic}", file=sys.stderr)
        return 1

    destination = args.output_dir.resolve() / "design-handoff.md"
    extras = [path for path in destination.parent.iterdir() if path != destination] if destination.parent.is_dir() else []
    if extras:
        print("output directory contains artifacts other than design-handoff.md", file=sys.stderr)
        return 1
    _write_atomic(destination, _with_receipt(final_text))
    if args.format == "json":
        print(json.dumps({"status": "sealed", "path": str(destination)}, sort_keys=True, separators=(",", ":")))
    else:
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
