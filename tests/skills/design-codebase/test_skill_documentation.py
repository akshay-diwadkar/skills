from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "design-codebase"


def test_out_of_scope_precedes_working_rules_and_gates() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert text.index("## Out of Scope") < text.index("## Working Rules") < text.index("## Gates")
    assert "Read this section before extending the skill." in text
    for responsibility in (
        "classify work as tiny, standard, high-risk",
        "full-repository propagation sweep",
        "file-level edits",
        "test or execution blueprints",
        "order migrations",
        "attack a proposed implementation",
    ):
        assert responsibility in text
    assert "Those responsibilities belong to `plan-change`." in text


def test_skill_has_one_final_artifact_and_no_legacy_contract_surfaces() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert text.count("### Gate ") == 7
    assert "emits exactly one document" in text
    assert "handoff.md" in text
    assert not (SKILL / "scripts" / "assessment_contract.py").exists()
    assert not (SKILL / "scripts" / "scaffold_assessment.py").exists()
    assert not (SKILL / "references" / "assessment-contract.json").exists()
    assert not (SKILL / "references" / "design-decision-rubric.md").exists()
    assert "L0" not in text
    assert "assessment-validation" not in text


def test_template_is_the_single_shape_source() -> None:
    template = (SKILL / "references" / "handoff-template.md").read_text(encoding="utf-8")
    expected = (
        "Problem & Scope",
        "Chosen Design & Depth Rationale",
        "Alternatives Considered",
        "Target Interface Contract",
        "Generality Justification",
        "Consolidation Considered",
        "Documentation Obligations",
        "Open Questions for the Planner",
    )
    assert template.count("## Evidence Ledger") == 1
    for heading in expected:
        assert template.count(f"## {heading}") == 1
