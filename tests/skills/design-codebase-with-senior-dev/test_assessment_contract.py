import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assessment_contract import load_contract, marker, render_scaffold, section_names  # noqa: E402

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
