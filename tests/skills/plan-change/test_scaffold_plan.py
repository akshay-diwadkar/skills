import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = REPO_ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "scaffold_plan.py"
sys.path.insert(0, str(SCAFFOLD.parent))
from plan_contract import load_contract, render_scaffold, section_names  # noqa: E402


def metadata(scaffold: str) -> dict:
    line = next(value for value in scaffold.splitlines() if value.startswith("<!-- plan-metadata:"))
    return json.loads(line.removeprefix("<!-- plan-metadata: ").removesuffix(" -->"))


def test_scaffold_supports_every_tier_and_intent() -> None:
    contract = load_contract()
    for tier in contract["tiers"]:
        for intent in contract["intents"]:
            scaffold = render_scaffold(tier, intent)
            assert contract["marker"] in scaffold
            assert metadata(scaffold)["final"] == {"intent": intent, "risk_domains": [], "tier": tier}
            assert [line[3:] for line in scaffold.splitlines() if line.startswith("## ")] == section_names(tier)


def test_scaffold_cli_prints_v4_contract() -> None:
    result = subprocess.run([sys.executable, str(SCAFFOLD), "--tier", "tiny", "--intent", "bug-fix"], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout == render_scaffold("tiny", "bug-fix")


def test_scaffold_records_required_attacks_and_domains() -> None:
    result = subprocess.run([sys.executable, str(SCAFFOLD), "--tier", "high-risk", "--intent", "feature", "--risk-domain", "security"], text=True, capture_output=True, check=True)
    contract = load_contract()
    for kind in contract["tiers"]["high-risk"]["required_ids"]:
        assert f"{kind}-1" in result.stdout
    for attack in [*contract["always_required_attacks"], *contract["domain_attacks"]["security"]]:
        assert f"A-{attack}:" in result.stdout or attack == "security"
    assert metadata(result.stdout)["final"]["risk_domains"] == ["security"]


def test_scaffold_rejects_duplicate_or_unknown_risk_domains() -> None:
    with pytest.raises(ValueError):
        render_scaffold("tiny", "bug-fix", ["security", "security"])
    with pytest.raises(ValueError):
        render_scaffold("tiny", "bug-fix", ["unknown"])
