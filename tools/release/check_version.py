#!/usr/bin/env python3
"""Check version alignment across repository manifests."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_PATH = ROOT / "VERSION"
PLUGIN_JSON_PATH = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON_PATH = ROOT / ".claude-plugin" / "marketplace.json"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def check_versions() -> list[str]:
    errors = []
    if not VERSION_PATH.is_file():
        return ["Missing VERSION file"]

    version = VERSION_PATH.read_text(encoding="utf-8").strip()
    if not SEMVER_RE.match(version):
        errors.append(f"VERSION '{version}' is not valid Semantic Versioning")

    if PLUGIN_JSON_PATH.is_file():
        data = json.loads(PLUGIN_JSON_PATH.read_text(encoding="utf-8"))
        if data.get("version") != version:
            errors.append(f".claude-plugin/plugin.json version '{data.get('version')}' != VERSION '{version}'")

    if MARKETPLACE_JSON_PATH.is_file():
        data = json.loads(MARKETPLACE_JSON_PATH.read_text(encoding="utf-8"))
        plugins = data.get("plugins", [])
        if plugins and plugins[0].get("version") != version:
            errors.append(f".claude-plugin/marketplace.json version '{plugins[0].get('version')}' != VERSION '{version}'")

    cursor_plugin = ROOT / ".cursor-plugin" / "plugin.json"
    if cursor_plugin.is_file():
        data = json.loads(cursor_plugin.read_text(encoding="utf-8"))
        if data.get("version") != version:
            errors.append(f".cursor-plugin/plugin.json version '{data.get('version')}' != VERSION '{version}'")

    cursor_market = ROOT / ".cursor-plugin" / "marketplace.json"
    if cursor_market.is_file():
        data = json.loads(cursor_market.read_text(encoding="utf-8"))
        plugins = data.get("plugins", [])
        if plugins and plugins[0].get("version") != version:
            errors.append(f".cursor-plugin/marketplace.json version '{plugins[0].get('version')}' != VERSION '{version}'")

    return errors


def main() -> int:
    errors = check_versions()
    if errors:
        print("Version check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Version check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
