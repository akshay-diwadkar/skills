import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "tests" / "plan-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))
import score_plan_evaluation  # noqa: E402


def test_evaluation_catalog_has_six_blind_cases() -> None:
    expectations = json.loads(score_plan_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    assert len(expectations) == 6
    for name, case in expectations.items():
        fixture = DEV_DIR / "evals" / "fixtures" / name
        assert (fixture / "prompt.md").is_file()
        assert list(fixture.rglob("*.py")), name
        assert set(case) >= {"tier", "grounding", "decisions", "propagation", "verification", "adversarial", "critical", "forbidden"}


def test_scorer_hard_fails_invalid_or_forbidden_plan() -> None:
    expectations = json.loads(score_plan_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["tiny-boundary-bug"]
    result = score_plan_evaluation.score(
        "# Return None from missing names\n## Change\nCH-1: return None\n",
        case,
        DEV_DIR / "evals" / "fixtures" / "tiny-boundary-bug",
    )
    assert result["passed"] is False
    assert result["hard_failures"]


def test_scorer_accepts_grounded_tiny_example() -> None:
    expectations = json.loads(score_plan_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    examples = REPO_ROOT / "plan-with-senior-dev" / "references" / "worked-examples.md"
    plan = re.findall(r"```plan\n(.*?)\n```", examples.read_text(encoding="utf-8"), re.DOTALL)[0]
    result = score_plan_evaluation.score(
        plan,
        expectations["tiny-boundary-bug"],
        DEV_DIR / "evals" / "fixtures" / "tiny-boundary-bug",
    )
    assert result["passed"] is True, result
    assert result["score"] == 100


def test_scorer_weights_sum_to_one_hundred() -> None:
    assert sum(score_plan_evaluation.WEIGHTS.values()) == 100


def test_scorer_keyword_groups_allow_explicit_semantic_alternatives() -> None:
    assert score_plan_evaluation._contains_groups('return ""', [["return", 'empty string||""']]) == (1, 1)


def test_root_cause_case_rejects_unrequested_interface_widening() -> None:
    expectations = json.loads(score_plan_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["root-cause-decoy"]
    plan = (
        "## Implementation Specification\n"
        "- CH-1: `src/config.py` | anchor: `retry_limit` | status: existing | "
        "change: widen to `str | int | None`.\n"
    )
    result = score_plan_evaluation.score(
        plan,
        case,
        DEV_DIR / "evals" / "fixtures" / "root-cause-decoy",
    )
    assert "forbidden:unrequested-input-widening" in result["hard_failures"]


def test_v1_baseline_uses_legacy_sections_without_applying_v2_shape() -> None:
    expectations = json.loads(score_plan_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    legacy = """# Handle missing names
## Outcome
Return an empty string for None.
## Evidence
- Fact: `src/names.py:1` normalize_name accepts nullable input.
- Fact: `src/names.py:2` strip dereferences it.
## Change
Update src/names.py normalize_name and tests/test_names.py; return empty string for None.
## Verification
Check None returns empty and Alice becomes alice.
## Assumptions
Low-impact: None.
"""
    result = score_plan_evaluation.score(
        legacy,
        expectations["tiny-boundary-bug"],
        DEV_DIR / "evals" / "fixtures" / "tiny-boundary-bug",
        contract_version=1,
    )
    assert result["contract_version"] == 1
    assert not any(item.startswith("validator:shape.") for item in result["hard_failures"])
