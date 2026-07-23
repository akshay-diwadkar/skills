#!/usr/bin/env python3
"""Validate tracked skill metadata and repository structure."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

import validate_repository  # noqa: E402


def main() -> int:
    return validate_repository.main()


if __name__ == "__main__":
    sys.exit(main())
