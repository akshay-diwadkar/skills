import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from optimization_contract import load_contract, marker, render_scaffold, section_names  # noqa: E402


def test_contract_declares_scopes_stages_and_exact_sections() -> None:
    contract = load_contract()

    assert contract["contract_version"] == 1
    assert contract["scopes"] == ["targeted", "sweep"]
    assert contract["stages"] == ["plan", "implementation"]
    assert section_names("plan") == contract["base_sections"]
    assert section_names("implementation")[-2:] == ["Execution Record", "Before/After Verification"]
    assert contract["max_sweep_candidates_per_wave"] == 3


def test_scaffold_contains_marker_records_and_stage_sections() -> None:
    plan = render_scaffold("targeted", "plan")
    implementation = render_scaffold("sweep", "implementation")

    assert marker("targeted", "plan") in plan
    for prefix in ("F", "CV", "B", "R", "C", "V", "X", "H"):
        assert f"- {prefix}-1:" in plan
    assert "## Execution Record" not in plan
    assert marker("sweep", "implementation") in implementation
    assert "- E-1:" in implementation
    assert "## Before/After Verification" in implementation


def test_scaffold_cli_prints_requested_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "scaffold_optimization.py"), "--scope", "sweep", "--stage", "plan"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert marker("sweep", "plan") in result.stdout
    assert "- Sweep status: incomplete" in result.stdout
    assert "## Execution Record" not in result.stdout
