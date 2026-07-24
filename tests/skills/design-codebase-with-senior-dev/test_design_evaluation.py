import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "design-codebase-with-senior-dev"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import score_design_evaluation  # noqa: E402
from assessment_contract import finalize_assessment_text  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def test_evaluation_catalog_has_fifteen_blind_cases() -> None:
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    assert len(expectations) >= 15, f"Expected at least 15 evaluation cases, got {len(expectations)}"
    for name, case in expectations.items():
        fixture = DEV_DIR / "evals" / "fixtures" / name
        assert (fixture / "prompt.md").is_file(), f"Missing prompt.md in fixture {name}"
        assert (fixture / "src" / "system.py").is_file(), f"Missing src/system.py in fixture {name}"
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
        level = case["level"]
        mode = "targeted"

        if name == "autonomous-discovery-obsolete-shim":
            mode = "autonomous-discovery"
            raw = valid_v2_assessment(level, mode=mode).replace("disposition: repay", "disposition: retire")
        elif name == "autonomous-refusal-tied-candidates":
            mode = "discovery-only"
            raw = valid_v2_assessment(level, mode=mode)
        elif name == "structural-debt-superficial-rejection":
            raw = valid_v2_assessment(level, mode=mode).replace("disposition: repay", "disposition: accept")
        elif name == "reject-unsafe-distributed-split":
            raw = valid_v2_assessment(level, mode=mode).replace("scenario: future pressure changes", "scenario: current transaction remains atomic")
        else:
            raw = valid_v2_assessment(level, mode=mode)

        finalized = finalize_assessment_text(raw, "discovery-only" if mode == "discovery-only" else level, mode=mode)
        result = score_design_evaluation.score(finalized, case, DEV_DIR / "evals" / "fixtures" / name)
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
    raw = valid_v2_assessment("L1").replace("follow-up: inspect history", "follow-up: implementation complete")
    finalized = finalize_assessment_text(raw, "L1")

    result = score_design_evaluation.score(
        finalized,
        case,
        DEV_DIR / "evals" / "fixtures" / "assess-and-implement-routing",
    )

    assert "forbidden:implementation-completed" in result["hard_failures"]


def test_scorer_weights_sum_to_one_hundred() -> None:
    assert sum(score_design_evaluation.WEIGHTS.values()) == 100
