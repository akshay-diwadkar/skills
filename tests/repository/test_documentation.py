"""Documentation regression tests for platform installation, compatibility claims, and layout integrity."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

sys.path.insert(0, str(REPO_ROOT / "tools" / "agents"))
from install_codex_agents import install_codex_agents  # noqa: E402


def test_reject_unqualified_marketplace_and_deprecated_local_plugin_load() -> None:
    """Ensure documentation rejects unqualified marketplace commands and deprecated /plugin load."""
    docs_to_check = [
        REPO_ROOT / "README.md",
        DOCS_DIR / "installation.md",
        DOCS_DIR / "getting-started.md",
        DOCS_DIR / "compatibility.md",
        DOCS_DIR / "release-process.md",
    ]

    for doc_path in docs_to_check:
        if not doc_path.is_file():
            continue
        text = doc_path.read_text(encoding="utf-8")
        rel_name = doc_path.relative_to(REPO_ROOT)

        # 1. Reject deprecated /plugin load
        assert "/plugin load" not in text, f"{rel_name} contains deprecated '/plugin load' command"

        # 2. Reject unqualified /plugin install engineering-skills (must use @)
        unqualified = re.search(r"/plugin\s+install\s+engineering-skills(?!\S)", text)
        assert unqualified is None, f"{rel_name} contains unqualified '/plugin install engineering-skills' command"


def test_readme_and_installation_guide_agreement() -> None:
    """Verify README.md and docs/installation.md agree on Claude marketplace install syntax."""
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    install_text = (DOCS_DIR / "installation.md").read_text(encoding="utf-8")

    expected_cmd = "/plugin install engineering-skills@engineering-skills-marketplace"
    assert expected_cmd in readme_text, "README.md missing qualified Claude marketplace install command"
    assert expected_cmd in install_text, "docs/installation.md missing qualified Claude marketplace install command"

    local_cmd = "claude --plugin-dir"
    assert local_cmd in readme_text, "README.md missing official local plugin-dir command"
    assert local_cmd in install_text, "docs/installation.md missing official local plugin-dir command"


def test_codex_compatibility_claims_accuracy() -> None:
    """Verify Codex support claims differentiate skills vs project-scoped agents installer."""
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    compat_text = (DOCS_DIR / "compatibility.md").read_text(encoding="utf-8")

    assert "install_codex_agents.py" in readme_text, "README.md should mention install_codex_agents.py"
    assert "install_codex_agents.py" in compat_text, "docs/compatibility.md should mention install_codex_agents.py"


def test_codex_agent_installer_creates_expected_layout(tmp_path: Path) -> None:
    """Verify tools/agents/install_codex_agents.py creates project-scoped .codex/ layout."""
    target_project = tmp_path / "my_project"
    target_project.mkdir()

    actions, errors = install_codex_agents(target_project, write=True)
    assert errors == [], f"Installer errors: {errors}"
    assert len(actions) > 0

    # Verify created layout
    codex_dir = target_project / ".codex"
    assert codex_dir.is_dir()
    assert (codex_dir / "config.toml").is_file()
    assert (codex_dir / "agents").is_dir()

    agent_files = list((codex_dir / "agents").glob("*.toml"))
    assert len(agent_files) >= 4
