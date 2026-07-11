import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plan_model import coverage_summary, parse_markdown, validate_semantics


def messages(text: str, tier: str = "standard", repo_root: Path | None = None) -> list[str]:
    return [str(item) for item in validate_semantics(text, tier, repo_root)]


def test_code_only_section_retains_content() -> None:
    document = parse_markdown("# Fix local parser\n## Change\n```python\nreturn True\n```\n")
    section = document.find_section("Change")
    assert section is not None
    assert section.has_content
    assert document.code_blocks[0].body == "return True"


def test_unclosed_fence_is_reported() -> None:
    errors = messages("# Fix local parser\n## Change\n```python\nreturn True\n", "tiny")
    assert any("markdown.fence.unclosed" in error for error in errors)


def test_missing_repo_citation_file_is_reported(tmp_path: Path) -> None:
    text = "# Fix local parser\n## Evidence\nFact: missing.py:9 is wrong\n"
    errors = messages(text, "tiny", tmp_path)
    assert any("semantic.evidence.missing_file" in error for error in errors)


def test_out_of_range_repo_citation_is_reported(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("one\ntwo\n", encoding="utf-8")
    errors = messages("# Fix local parser\n## Evidence\nFact: real.py:9 is wrong\n", "tiny", tmp_path)
    assert any("semantic.evidence.line_out_of_range" in error for error in errors)


def test_valid_repo_citation_passes(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("one\ntwo\n", encoding="utf-8")
    errors = messages("# Fix local parser\n## Evidence\nFact: real.py:2 is wrong\n", "tiny", tmp_path)
    assert not any("semantic.evidence" in error for error in errors)


def test_standard_requires_traceability_ids() -> None:
    errors = messages("# Fix local parser\n## Outcome and Scope\nReturns success\n")
    assert any("missing_sc_ids" in error for error in errors)
    assert any("missing_ch_ids" in error for error in errors)
    assert any("missing_t_ids" in error for error in errors)


def test_orphan_criterion_is_reported() -> None:
    text = (
        "# Fix local parser\n"
        "## Outcome and Scope\nSC-1: Returns success\n"
        "## Implementation Specification\nCH-1: Fix parser\n"
        "## Verification and Risks\nT-1: Assert success\n"
        "## Traceability and Constraints\nSC-2 -> CH-1 -> T-1\n"
    )
    errors = messages(text)
    assert any("criterion_unmapped" in error for error in errors)


def test_propagation_update_requires_change_owner() -> None:
    text = "# Fix local parser\n## Change Propagation Map\nparser -> src/a.py:1 - update required: yes\n"
    errors = messages(text)
    assert any("semantic.propagation.owner_missing" in error for error in errors)


def test_boolean_expectation_contradiction_is_reported() -> None:
    text = "# Fix local parser\n## Verification\nGiven input 1, assert output true and assert output false.\n"
    errors = messages(text, "tiny")
    assert any("semantic.expectation.contradiction" in error for error in errors)


def test_p1_risk_requires_action_and_owner() -> None:
    text = "# Fix local parser\n## Verification and Risks\nR-1 P1: timeout loses work.\n"
    errors = messages(text)
    assert any("semantic.risk.action_owner_missing" in error for error in errors)


def test_interface_change_requires_current_evidence() -> None:
    text = (
        "# Update public parser interface\n"
        "## Evidence and Decisions\nNo citation supplied\n"
        "## Implementation Specification\nCH-1: Change the API interface\n"
        "```typescript\ninterface Parser { run(): boolean }\n```\n"
    )
    errors = messages(text)
    assert any("semantic.interface.current_evidence_missing" in error for error in errors)


def test_coverage_reports_traceability() -> None:
    text = (
        "# Fix local parser\n"
        "## Outcome and Scope\nSC-1: Returns success\n"
        "## Implementation Specification\nCH-1: Fix parser\n"
        "## Traceability and Constraints\nSC-1 -> CH-1 -> T-1\n"
        "## Verification and Risks\nT-1: Assert success\n"
    )
    coverage = coverage_summary(text)
    assert coverage["success_criteria"] == 1
    assert coverage["changes"] == 1
    assert coverage["tests"] == 1
    assert coverage["traceability_complete"] is True
