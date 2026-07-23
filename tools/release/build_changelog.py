#!/usr/bin/env python3
"""Validate CHANGELOG.md formatting and presence of current version."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
VERSION_PATH = ROOT / "VERSION"


def validate_changelog() -> list[str]:
    errors = []
    if not CHANGELOG_PATH.is_file():
        return ["Missing CHANGELOG.md"]

    if not VERSION_PATH.is_file():
        return ["Missing VERSION file"]

    version = VERSION_PATH.read_text(encoding="utf-8").strip()
    text = CHANGELOG_PATH.read_text(encoding="utf-8")

    if f"[{version}]" not in text and f"## {version}" not in text:
        errors.append(f"CHANGELOG.md does not record current version '{version}'")

    return errors


def main() -> int:
    errors = validate_changelog()
    if errors:
        print("Changelog validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Changelog validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
