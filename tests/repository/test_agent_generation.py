from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "catalog"))

import sync_catalog  # noqa: E402


def test_sync_catalog_has_no_diffs() -> None:
    diffs = sync_catalog.sync_all(write=False)
    assert diffs == [], f"Stale surfaces found: {diffs}"


def test_generated_adapters_contain_provenance_and_parse() -> None:
    agents_cat = sync_catalog.load_agents_catalog()
    for agent in agents_cat.get("agents", []):
        name = agent["name"]

        # Claude adapter check
        claude_file = REPO_ROOT / "agents" / "claude" / f"{name}.md"
        assert claude_file.is_file()
        claude_text = claude_file.read_text(encoding="utf-8")
        assert "<!-- Generated from catalog/agents.yaml" in claude_text
        assert f"name: {name}" in claude_text

        # Cursor adapter check
        cursor_file = REPO_ROOT / "agents" / "cursor" / f"{name}.md"
        assert cursor_file.is_file()
        cursor_text = cursor_file.read_text(encoding="utf-8")
        assert "<!-- Generated from catalog/agents.yaml" in cursor_text
        assert f"name: {name}" in cursor_text

        # Codex adapter check
        codex_file = REPO_ROOT / ".codex" / "agents" / f"{name}.toml"
        assert codex_file.is_file()
        with codex_file.open("rb") as f:
            data = tomllib.load(f)
        assert data["name"] == name
        assert "developer_instructions" in data
