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
    assert "version: 1.3.0" in text
    assert "--verify-evidence" in text


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


def test_pipeline_documentation_and_changelog_are_present() -> None:
    readme = (SKILL / "README.md").read_text(encoding="utf-8")
    assert "scope-issue" in readme
    assert "design-codebase" in readme
    assert "prepare_plan.py" in readme
    assert "--request-file" in readme
    assert "request_sha256" in readme
    for limitation in ("authenticate", "evidence freshness", "Git commit", "correct and complete"):
        assert limitation in readme

    for skill_name in ("plan-change", "scope-issue"):
        cross_link = ROOT / "skills" / "engineering" / skill_name / "README.md"
        assert "../design-codebase/README.md" in cross_link.read_text(encoding="utf-8")

    changelog = (SKILL / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.1.0 - 2026-07-29" in changelog
    assert "SHA-256" in changelog
