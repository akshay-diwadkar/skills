import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev"
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assessment_contract import (  # noqa: E402
    finalize_assessment_text,
    load_contract,
    marker,
    render_scaffold,
    section_names,
)
from check_assessment import validate  # noqa: E402

LEVELS = ("L0", "L1", "L2", "L3")


def test_contract_declares_exact_sections_for_every_level() -> None:
    contract = load_contract()

    assert contract["contract_version"] == 2
    assert section_names("L0") == contract["base_sections"]
    assert section_names("L1")[-1] == "Local Simplification and Preservation"
    assert section_names("L2")[-1] == "Operational Semantics"
    assert section_names("L3")[-1] == "System Ownership and Evolution"


def test_scaffold_contains_level_marker_and_required_records() -> None:
    for level in LEVELS:
        scaffold = render_scaffold(level)

        assert marker(level) in scaffold
        assert "<!-- design-assessment-contract: 2;" in scaffold
        assert "## Decision Summary" in scaffold
        assert "- C-1:" in scaffold
        assert "- H-1: status: assessment-only" in scaffold
        assert f"- D-1: level: {level}" in scaffold
        assert "- V-1:" in scaffold


def test_scaffold_cli_prints_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "scaffold_assessment.py"), "--level", "L2"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert marker("L2") in result.stdout
    assert "## Migration and Rollback" in result.stdout
    assert "## System Ownership and Evolution" not in result.stdout


def test_worked_examples_pass_checker_and_finalizer(tmp_path: Path) -> None:
    # Setup mock files for worked examples
    billing = tmp_path / "billing"
    billing.mkdir()
    (billing / "formatter.py").write_text("def render_invoice(): pass\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_formatter.py").write_text("def test_compact_and_detailed(): pass\n", encoding="utf-8")
    payments = tmp_path / "payments"
    payments.mkdir()
    (payments / "service.py").write_text("import provider_sdk\n", encoding="utf-8")

    examples_file = SKILL_DIR / "references" / "worked-examples.md"
    content = examples_file.read_text(encoding="utf-8")
    example_blocks = [("# Assessment:" + block) for block in content.split("# Assessment:") if block.strip() and "<!-- design-assessment-contract:" in block]

    assert len(example_blocks) >= 2, f"Expected at least 2 worked examples, found {len(example_blocks)}"

    for example in example_blocks:
        match = re.search(r"level: (L[0-3])", example)
        assert match is not None, f"Example missing level marker:\n{example}"
        level = match.group(1)

        raw_diags = validate(example, level, tmp_path)
        assert raw_diags == [], f"Worked example for {level} failed draft validation:\n{raw_diags}"

        finalized = finalize_assessment_text(example, level)
        final_diags = validate(finalized, level, tmp_path, require_finalized=True)
        assert final_diags == [], f"Worked example for {level} failed finalized validation:\n{final_diags}"
