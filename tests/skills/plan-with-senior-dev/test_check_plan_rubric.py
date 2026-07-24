import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from check_plan_rubric import validate  # noqa: E402

EXAMPLES = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "references" / "worked-examples.md"
TIERS = ("tiny", "standard", "high-risk")


def plan(tier: str) -> str:
    blocks = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)
    return blocks[TIERS.index(tier)]


def codes(text: str, tier: str) -> set[str]:
    return {item.code for item in validate(text, tier)}


def test_examples_satisfy_v3_rubric() -> None:
    for tier in TIERS:
        assert validate(plan(tier), tier) == []


def test_fact_requires_citation_anchor_and_observation() -> None:
    broken = plan("tiny").replace(" | anchor: `normalize_name`", "")
    assert "rubric.fact.format" in codes(broken, "tiny")


def test_decision_requires_selected_reason_and_rejected_alternative() -> None:
    broken = re.sub(r"\| rejected:.*", "", plan("tiny"), count=1)
    assert "rubric.decision.format" in codes(broken, "tiny")


def test_change_requires_existing_or_new_status() -> None:
    broken = plan("tiny").replace("status: existing", "status: maybe", 1)
    assert "rubric.change.format" in codes(broken, "tiny")


def test_test_requires_exact_given_expect_and_command() -> None:
    broken = plan("tiny").replace(" | expect:", " | result:", 1)
    assert "rubric.test.format" in codes(broken, "tiny")


def test_attacks_require_status_and_evidence_but_not_findings() -> None:
    all_dismissed = plan("tiny").replace("A2: repaired", "A2: dismissed")
    assert "rubric.attack.missing" not in codes(all_dismissed, "tiny")
    missing = re.sub(r"^- A2:.*\n", "", plan("tiny"), flags=re.MULTILINE)
    assert "rubric.attack.missing" in codes(missing, "tiny")


def test_high_risk_requires_complete_rollout_and_durable_rollback() -> None:
    broken = plan("high-risk").replace(
        "Deployment order is new consumer behavior first, then the schema and producer.",
        "Deploy carefully.",
    )
    assert "rubric.compatibility.incomplete" in codes(broken, "high-risk")


def test_high_risk_rollout_accepts_clear_equivalent_operational_terms() -> None:
    equivalent = plan("high-risk").replace(
        "Deployment order is new consumer behavior first, then the schema and producer. Old readers ignore the new dictionary key; new readers return `unknown` for old events. Monitor empty-tenant validation failures and the fraction of events without tenant identity. Stop rollout if validation failures exceed the existing error baseline or any consumer rejects the additive key.",
        "Legacy readers tolerate the optional field. Deploy updated readers first, before target writers. Observe validation metrics; halt if either exceeds baseline.",
    )
    assert "rubric.compatibility.incomplete" not in codes(equivalent, "high-risk")


def test_p0_and_p1_risks_require_resolution_ownership_format() -> None:
    broken = plan("high-risk").replace(" | Resolution: CH-2/T-2", "")
    assert "rubric.risk.format" in codes(broken, "high-risk")
