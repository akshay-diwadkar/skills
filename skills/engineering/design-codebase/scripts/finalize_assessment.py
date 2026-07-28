#!/usr/bin/env python3
"""Validate and emit the sole design-codebase artifact as handoff.md."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from handoff_contract import normalize_markdown, validate_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()

    if not args.repo_root.is_absolute() or not args.repo_root.is_dir():
        parser.error("--repo-root must be an absolute repository directory")
    if not args.output_dir.is_absolute():
        parser.error("--output-dir must be absolute")
    if not args.draft.is_file():
        parser.error("draft must be a Markdown file")

    text = args.draft.read_text(encoding="utf-8")
    _handoff, diagnostics = validate_handoff(text, args.repo_root)
    if diagnostics:
        print("Cannot finalize invalid design handoff:", file=sys.stderr)
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}", file=sys.stderr)
        return 1

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "handoff.md"
    normalized = normalize_markdown(text)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=output_dir,
            prefix=".handoff-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(normalized)
            temporary_name = temporary.name
        os.replace(temporary_name, destination)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
