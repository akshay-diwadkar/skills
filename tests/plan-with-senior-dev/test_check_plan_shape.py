import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "plan-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from check_plan_shape import validate  # noqa: E402
from plan_contract import load_contract, section_names  # noqa: E402


EXAMPLES = REPO_ROOT / "plan-with-senior-dev" / "references" / "worked-examples.md"
TIERS = ("tiny", "standard", "high-risk")


def plan(tier: str) -> str:
    blocks = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)
    return blocks[TIERS.index(tier)]


def codes(text: str, tier: str = "tiny") -> set[str]:
    return {item.code for item in validate(text, tier)}


def test_contract_declares_exact_v2_sections_for_each_tier() -> None:
    contract = load_contract()
    assert contract["contract_version"] == 2
    assert section_names("tiny") == contract["base_sections"]
    assert section_names("high-risk")[-2:] == ["Compatibility and Rollout", "Durable Rollback"]


def test_published_examples_have_valid_shape() -> None:
    for tier in TIERS:
        assert not [item for item in validate(plan(tier), tier) if not item.is_warning]


def test_missing_contract_marker_has_specific_v1_diagnostic() -> None:
    assert "contract.version.legacy" in codes(plan("tiny").replace("<!-- plan-contract: 2 -->", ""))


def test_legacy_heading_is_not_accepted_as_alias() -> None:
    assert "shape.section.missing" in codes(plan("tiny").replace("## Outcome and Scope", "## Goal"))


def test_unfilled_scaffold_placeholder_is_rejected() -> None:
    assert "shape.scaffold.placeholder" in codes(plan("tiny").replace("None.", "Replace with assumptions."))


def test_descriptive_titles_are_not_limited_to_a_verb_dictionary() -> None:
    assert "shape.title.not_descriptive" not in codes(
        plan("tiny").replace("# Handle Missing Names Without Changing Valid Normalization", "# Negotiate CSV for Completed Reports")
    )
    assert "shape.title.not_descriptive" in codes(
        plan("tiny").replace("# Handle Missing Names Without Changing Valid Normalization", "# Implementation Plan")
    )


def test_excessive_length_is_advisory_not_hard_failure() -> None:
    text = plan("tiny") + "\n" + "\n".join(f"extra evidence sentence {index}" for index in range(100))
    findings = validate(text, "tiny")
    length = next(item for item in findings if item.code == "shape.line_count.repetition_risk")
    assert length.is_warning


def test_unclosed_fence_is_reported() -> None:
    assert "markdown.fence.unclosed" in codes(plan("tiny") + "\n```python\nvalue = 1")
