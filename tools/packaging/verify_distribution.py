#!/usr/bin/env python3
"""Verify built distribution tree for runtime completeness and clean boundaries."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "packaging"))

from build_distribution import build_distribution  # noqa: E402


def verify_distribution_tree(dist_path: Path) -> list[str]:
    errors = []

    # Ensure plugin manifests exist
    claude_json = dist_path / ".claude-plugin" / "plugin.json"
    if not claude_json.is_file():
        errors.append("Distribution missing .claude-plugin/plugin.json")

    cursor_json = dist_path / ".cursor-plugin" / "plugin.json"
    if not cursor_json.is_file():
        errors.append("Distribution missing .cursor-plugin/plugin.json")

    agents_dir = dist_path / "agents"
    if not agents_dir.is_dir():
        errors.append("Distribution missing agents directory")

    # Check for forbidden development files
    forbidden_names = {"browser_smoke.py", "conftest.py", "debug_hash.py", "test_*.py"}
    for p in dist_path.rglob("*"):
        if p.name in forbidden_names or p.name.startswith("test_") or "evals" in p.parts:
            errors.append(f"Distribution contains forbidden development artifact: {p.relative_to(dist_path)}")

    return errors


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="verify-dist-"))
    try:
        dist_path = build_distribution(temp_dir)
        errors = verify_distribution_tree(dist_path)
        if errors:
            print("Distribution verification failed:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        print("Distribution verification passed.")
        return 0
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
