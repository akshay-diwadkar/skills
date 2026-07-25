"""Documentation regression tests for skill installation, links, and layout integrity."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"


def test_skills_sh_installation_documentation() -> None:
    """Verify README.md and docs/installation.md describe skills.sh installation."""
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    install_text = (DOCS_DIR / "installation.md").read_text(encoding="utf-8")

    expected_cmd = "npx skills add akshay-diwadkar/skills"
    assert expected_cmd in readme_text, "README.md missing skills.sh install command"
    assert expected_cmd in install_text, "docs/installation.md missing skills.sh install command"


def test_validation_scope_documentation() -> None:
    """Verify documentation accurately describes automated repository validation and avoids overclaiming."""
    for md_file in REPO_ROOT.rglob("*.md"):
        if ".scratch" in md_file.parts or ".git" in md_file.parts or ".pytest_cache" in md_file.parts:
            continue
        text = md_file.read_text(encoding="utf-8")
        assert "guarantees compatibility across every platform" not in text, (
            f"{md_file.relative_to(REPO_ROOT)} overclaims platform compatibility guarantee"
        )

