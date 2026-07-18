import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "tests" / "design-codebase-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))

import score_design_evaluation  # noqa: E402
from test_check_assessment import assessment  # noqa: E402


def test_evaluation_catalog_has_eight_blind_cases() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    assert len(expectations) == 8
    for name, case in expectations.items():
        fixture = DEV_DIR / "evals" / "fixtures" / name
        assert (fixture / "prompt.md").is_file()
        assert (fixture / "src" / "system.py").is_file()
        assert set(case) >= {
            "level",
            "grounding",
            "classification",
            "preservation",
            "alternatives",
            "migration",
            "handoff",
            "critical",
            "forbidden",
        }


def test_all_fixture_expectations_accept_grounded_contract_examples() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    for name, case in expectations.items():
        text = assessment(case["level"])
        if name == "reject-unsafe-distributed-split":
            text = text.replace("scenario: future pressure changes", "scenario: current transaction remains atomic")
        result = score_design_evaluation.score(text, case, DEV_DIR / "evals" / "fixtures" / name)
        assert result["passed"] is True, (name, result)
        assert result["score"] == 100, (name, result)


def test_scorer_hard_fails_invalid_assessment() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["l0-long-file-decoy"]

    result = score_design_evaluation.score(
        "# Architecture\n## Decision\nUse services.\n",
        case,
        DEV_DIR / "evals" / "fixtures" / "l0-long-file-decoy",
    )

    assert result["passed"] is False
    assert result["hard_failures"]


def test_scorer_rejects_forbidden_implementation_claim() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["assess-and-implement-routing"]
    text = assessment("L1").replace("follow-up: inspect history", "follow-up: implementation complete")

    result = score_design_evaluation.score(
        text,
        case,
        DEV_DIR / "evals" / "fixtures" / "assess-and-implement-routing",
    )

    assert "forbidden:implementation-completed" in result["hard_failures"]


def test_scorer_weights_sum_to_one_hundred() -> None:
    assert sum(score_design_evaluation.WEIGHTS.values()) == 100
