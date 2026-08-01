import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "SKILL.md"
CONTRACT = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "references" / "optimization-contract.md"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from optimization_contract import load_contract, marker, render_scaffold, section_names  # noqa: E402


def test_contract_declares_first_class_paths_and_exact_shapes() -> None:
    contract = load_contract()

    assert contract["contract_version"] == 2
    assert contract["paths"] == ["fast", "full"]
    assert contract["fast"]["exact_record_counts"] == {"F": 1, "B": 1, "C": 1}
    assert section_names("fast", "implementation") == ["Fast Path Decision"]
    assert section_names("full", "implementation")[-2:] == ["Execution Record", "Before/After Verification"]
    assert contract["max_sweep_candidates_per_wave"] == 3


def test_compact_contract_is_required_before_full_path_evidence() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "references/optimization-contract.md" in text
    assert "references/optimization-techniques.md" in text


def test_compact_contract_covers_contract_and_handoff_vocabulary() -> None:
    contract = load_contract()
    text = CONTRACT.read_text(encoding="utf-8")

    for coordinate in (*contract["paths"], *contract["scopes"], *contract["stages"]):
        assert f"`{coordinate}`" in text
    for required in (
        "baseline",
        "verification",
        "rollback",
        "Implementation remains unauthorized",
        "canonical result",
    ):
        assert required in text


def test_fast_scaffold_is_minimal_and_full_scaffold_retains_records() -> None:
    fast = render_scaffold("fast", "targeted", "implementation")
    full = render_scaffold("full", "sweep", "implementation")

    assert marker("fast", "targeted", "implementation") in fast
    for prefix in ("F", "B", "C"):
        assert fast.count(f"- {prefix}-1:") == 1
    for forbidden in ("CV-1", "R-1", "V-1", "X-1", "H-1", "E-1"):
        assert forbidden not in fast
    assert marker("full", "sweep", "implementation") in full
    for prefix in ("F", "CV", "B", "R", "C", "V", "X", "H", "E"):
        assert f"- {prefix}-1:" in full


def test_fast_contract_rejects_plan_or_sweep() -> None:
    with pytest.raises(ValueError, match="targeted scope and implementation"):
        render_scaffold("fast", "targeted", "plan")
    with pytest.raises(ValueError, match="targeted scope and implementation"):
        render_scaffold("fast", "sweep", "implementation")


def test_scaffold_cli_requires_path_and_prints_requested_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "scaffold_optimization.py"),
            "--path",
            "full",
            "--scope",
            "sweep",
            "--stage",
            "plan",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert marker("full", "sweep", "plan") in result.stdout
    assert "- Sweep status: incomplete" in result.stdout
