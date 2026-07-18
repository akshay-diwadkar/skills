import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "tests" / "optimize-codebase-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))

import score_optimization_evaluation  # noqa: E402
from report_factory import valid_report  # noqa: E402


def test_evaluation_catalog_has_eight_blind_cases() -> None:
    expectations = json.loads(score_optimization_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    assert len(expectations) == 8
    for name, case in expectations.items():
        fixture = DEV_DIR / "evals" / "fixtures" / name
        assert (fixture / "prompt.md").is_file()
        assert (fixture / "src" / "system.py").is_file()
        assert set(case) >= {
            "scope", "stage", "grounding", "coverage", "baseline", "ecosystem", "gating", "plan",
            "safety", "critical", "forbidden",
        }


def test_all_fixture_expectations_accept_grounded_contract_reports() -> None:
    expectations = json.loads(score_optimization_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    for name, case in expectations.items():
        report = valid_report(
            case["scope"],
            case["stage"],
            investigate=bool(case.get("investigate")),
            static=bool(case.get("static")),
            inconclusive=bool(case.get("inconclusive")),
            note=str(case["acceptance_note"]),
        )
        result = score_optimization_evaluation.score(report, case, DEV_DIR / "evals" / "fixtures" / name)
        assert result["passed"] is True, (name, result)
        assert result["score"] == 100, (name, result)


def test_scorer_hard_fails_invalid_report() -> None:
    expectations = json.loads(score_optimization_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["hot-path-decoy"]

    result = score_optimization_evaluation.score(
        "# Optimize\n## Candidate Decisions\nUse a cache.\n",
        case,
        DEV_DIR / "evals" / "fixtures" / "hot-path-decoy",
    )

    assert result["passed"] is False
    assert result["hard_failures"]


def test_scorer_rejects_plan_only_implementation_claim() -> None:
    expectations = json.loads(score_optimization_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["authorization-routing"]
    report = valid_report(note=case["acceptance_note"]).replace(
        "Residual risk: Production workload variance", "Residual risk: implementation complete; Production workload variance"
    )

    result = score_optimization_evaluation.score(
        report,
        case,
        DEV_DIR / "evals" / "fixtures" / "authorization-routing",
    )

    assert "forbidden:plan-only-mutation" in result["hard_failures"]


def test_scorer_weights_sum_to_one_hundred() -> None:
    assert sum(score_optimization_evaluation.WEIGHTS.values()) == 100
