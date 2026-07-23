import subprocess
import sys
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "scripts" / "scaffold_plan.py"
sys.path.insert(0, str(SCAFFOLD.parent))
from plan_contract import load_contract, render_scaffold, section_names  # noqa: E402
from plan_model import parse_markdown  # noqa: E402


def test_scaffold_cli_supports_every_tier_and_task_type() -> None:
    contract = load_contract()
    for tier in contract["tiers"]:
        for task_type in contract["task_types"]:
            scaffold = render_scaffold(tier, task_type)
            assert contract["marker"] in scaffold
            assert f"tier: {tier}; task-type: {task_type}" in scaffold
            document = parse_markdown(scaffold)
            assert [section.name for section in document.sections if section.level == 2] == section_names(tier)


def test_scaffold_cli_prints_rendered_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--tier", "tiny", "--task-type", "bug-fix"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == render_scaffold("tiny", "bug-fix")


def test_scaffold_contains_every_required_record_and_attack_placeholder() -> None:
    contract = load_contract()
    result = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--tier", "high-risk", "--task-type", "security"],
        text=True,
        capture_output=True,
        check=True,
    )
    for kind in contract["tiers"]["high-risk"]["required_ids"]:
        assert re.search(rf"\b{kind}-1\b", result.stdout)
    for attack in contract["tiers"]["high-risk"]["required_attacks"]:
        assert f"- {attack}:" in result.stdout


def test_scaffold_requires_blueprints_only_for_non_tiny_tiers() -> None:
    assert "### Execution Blueprint:" not in render_scaffold("tiny", "bug-fix")
    assert "### Execution Blueprint: CH-1" in render_scaffold("standard", "feature")
    assert "```pseudocode" in render_scaffold("high-risk", "concurrency")
