from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "design-codebase"


def test_authority_boundary_and_gates_remain_disclosed() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    protocol = (SKILL / "references" / "design-protocol.md").read_text(encoding="utf-8")
    for responsibility in (
        "classify implementation tier",
        "full propagation",
        "file-level edits",
        "test or execution blueprints",
        "order\nmigrations",
        "attack an implementation",
    ):
        assert responsibility in text
    assert "Those responsibilities\nbelong to `plan-change`." in text
    assert protocol.count("## ") == 7


def test_skill_has_one_final_artifact_and_no_legacy_contract_surfaces() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    protocol = (SKILL / "references" / "design-protocol.md").read_text(encoding="utf-8")
    assert protocol.count("## ") == 7
    assert "emits exactly one `design-handoff.md`" in protocol
    assert "design-handoff.md" in text
    assert not (SKILL / "scripts" / "assessment_contract.py").exists()
    assert not (SKILL / "scripts" / "scaffold_assessment.py").exists()
    assert not (SKILL / "references" / "assessment-contract.json").exists()
    assert not (SKILL / "references" / "design-decision-rubric.md").exists()
    assert "L0" not in text
    assert "assessment-validation" not in text
    assert "version: 3.0.1" in text
    assert "seal_assessment.py" in protocol
    assert "check_assessment.py" not in protocol
    assert "finalize_assessment.py" not in protocol


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
    assert template.count("- Coupling direction:") == 2


def test_shared_vocabulary_is_compact_and_gate_integrated() -> None:
    protocol = (SKILL / "references" / "design-protocol.md").read_text(encoding="utf-8")
    definitions = {
        "Owner": "Repository area responsible",
        "Boundary": "Point where responsibility",
        "Contract": "Caller-visible inputs",
        "Depth": "Useful behavior hidden",
        "Volatility": "Likelihood that a detail changes",
        "Propagation": "Number and distance",
        "Locality": "Degree to which related behavior",
        "Deletion test": "Remove an abstraction",
        "Second-use test": "Generalize only when",
        "Coupling direction": "Direction in which dependency knowledge",
    }
    for term, definition in definitions.items():
        assert protocol.count(f"| {term} |") == 1
        assert definition in protocol
    assert "Do not score them or turn\nthem into a checklist." in protocol
    assert protocol.count("## ") == 7


def test_pipeline_documentation_and_changelog_are_present() -> None:
    readme = (SKILL / "README.md").read_text(encoding="utf-8")
    assert "scope-issue" in readme
    assert "design-codebase" in readme
    assert "draft_file" in readme
    assert "request_file" in readme
    assert "plan-contract v6" in readme
    assert "request digest" in readme

    for skill_name in ("plan-change", "scope-issue"):
        cross_link = ROOT / "skills" / "engineering" / skill_name / "README.md"
        assert "../design-codebase/README.md" in cross_link.read_text(encoding="utf-8")

    changelog = (SKILL / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.1.0 - 2026-07-29" in changelog
    assert "SHA-256" in changelog
