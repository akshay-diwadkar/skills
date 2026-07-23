from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))

import sync_catalog  # noqa: E402


def test_platform_manifests_validity_and_version_sync() -> None:
    version = sync_catalog.get_version()

    # Claude plugin manifest
    claude_plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    assert claude_plugin.is_file()
    claude_data = json.loads(claude_plugin.read_text(encoding="utf-8"))
    assert claude_data["version"] == version
    assert claude_data["agents"] == "./agents/claude/"

    # Cursor plugin manifest
    cursor_plugin = REPO_ROOT / ".cursor-plugin" / "plugin.json"
    assert cursor_plugin.is_file()
    cursor_data = json.loads(cursor_plugin.read_text(encoding="utf-8"))
    assert cursor_data["version"] == version
    assert cursor_data["skills"] == "./skills/"
    assert cursor_data["agents"] == "./agents/cursor/"
