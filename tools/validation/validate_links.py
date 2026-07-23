#!/usr/bin/env python3
"""Validate relative markdown file links across skills and docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK_RE = re.compile(r"\[.*?\]\((?!https?:\/\/|mailto:)(.*?)\)")


def validate_markdown_links() -> list[str]:
    errors = []
    for md_file in ROOT.rglob("*.md"):
        if any(part.startswith(".") for part in md_file.parts):
            continue
        text = md_file.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(1).split("#")[0]
            if not target:
                continue
            resolved = (md_file.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{md_file.relative_to(ROOT)}: broken link to '{target}'")
    return errors


def main() -> int:
    errors = validate_markdown_links()
    if errors:
        print("Link validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Link validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
