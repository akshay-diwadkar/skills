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


def test_permission_boundaries_and_read_only_enforcement() -> None:
    agents_cat = sync_catalog.load_agents_catalog()

    for agent in agents_cat.get("agents", []):
        name = agent["name"]
        repo_write = agent.get("access", {}).get("repository_write", False)

        # Claude tools check
        claude_file = REPO_ROOT / "agents" / "claude" / f"{name}.md"
        claude_text = claude_file.read_text(encoding="utf-8")
        if not repo_write:
            assert "  - Edit" not in claude_text
            assert "  - Write" not in claude_text
        else:
            assert "  - Edit" in claude_text
            assert "  - Write" in claude_text

        # Cursor readonly check
        cursor_file = REPO_ROOT / "agents" / "cursor" / f"{name}.md"
        cursor_text = cursor_file.read_text(encoding="utf-8")
        if not repo_write:
            assert "readonly: true" in cursor_text
        else:
            assert "readonly: false" in cursor_text

        # Codex sandbox_mode check
        codex_file = REPO_ROOT / ".codex" / "agents" / f"{name}.toml"
        with codex_file.open("rb") as f:
            codex_data = tomllib.load(f)
        if not repo_write:
            assert codex_data["sandbox_mode"] == "read-only"
        else:
            assert codex_data["sandbox_mode"] == "workspace-write"
