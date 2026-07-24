"""Tests for confirmation gating behavior in design-codebase-with-senior-dev skill."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_MD = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "SKILL.md"
RUBRIC_MD = (
    REPO_ROOT
    / "skills"
    / "engineering"
    / "design-codebase-with-senior-dev"
    / "references"
    / "design-decision-rubric.md"
)


def test_skill_instructions_specify_material_ambiguity_confirmation_only() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    # Verify non-negotiable #6 specifies confirmation ONLY when material ambiguity remains
    assert "Ask for user confirmation ONLY when material ambiguity remains" in text
    assert "continue automatically and record the resolved frame" in text

    # Verify Gate 3 rules
    assert "Ask the user for clarification ONLY when a material ambiguity remains" in text
    assert "continue automatically without adding a mandatory confirmation pause" in text
    assert "do not pause or block an otherwise decision-complete assessment" in text
    assert "do not choose an unresolved product or contract decision on the user's behalf" in text


def test_rubric_aligns_with_automatic_continuation() -> None:
    text = RUBRIC_MD.read_text(encoding="utf-8")
    assert "Ask the user for confirmation ONLY when a material ambiguity remains" in text
    assert "proceed automatically without a mandatory confirmation pause" in text


def test_material_ambiguity_categories_are_explicit() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    for category in [
        "user-visible behavior",
        "public or shared contracts",
        "persisted state",
        "state ownership",
        "security or authorization",
        "failure semantics",
        "migration and rollback constraints",
        "external effects",
        "deployment compatibility",
    ]:
        assert category in text
