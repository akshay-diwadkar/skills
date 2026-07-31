from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "technical-communication" / "manualize"


def test_skill_documents_operations_profiles_and_validation_pipeline() -> None:
    documents = [(SKILL / "SKILL.md").read_text(encoding="utf-8")]
    documents.extend(path.read_text(encoding="utf-8") for path in (SKILL / "references").glob("*.md"))
    text = "\n".join(documents)
    normalized = " ".join(text.split())
    for required in (
        "operation: write",
        "operation: audit",
        "profile: strict",
        "profile: standard",
        "check_manual_language.py",
        "check_manual.py",
        "finalize_manual.py",
        "manual-audit.md",
        "manual-audit.json",
    ):
        assert required in text
    assert "never claim official ASD-STE100 compliance" in normalized
    assert "approved-word dictionary" in normalized
    assert "Validation does not establish independent factual truth" in normalized


def test_every_shipped_reference_schema_and_template_is_meaningful() -> None:
    for directory in ("references", "schemas", "templates"):
        paths = sorted(path for path in (SKILL / directory).iterdir() if path.is_file())
        assert paths
        assert all(path.stat().st_size > 100 for path in paths)
