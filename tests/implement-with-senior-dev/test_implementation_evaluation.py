import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "tests" / "implement-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))

import score_implementation_evaluation  # noqa: E402


def test_expectations_cover_every_required_reliability_scenario() -> None:
    expectations = json.loads(score_implementation_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    assert set(expectations) == {
        "v3-tiny-local-bug",
        "v3-standard-mechanical-propagation",
        "legacy-tiny-plan",
        "stale-plan-contradiction",
        "dirty-target-refusal",
        "preexisting-baseline-failure",
        "unexpected-generated-artifact",
        "high-risk-external-stop",
        "complete-error-branches",
        "verification-tool-unavailable",
    }
    for case_id in expectations:
        fixture = DEV_DIR / "evals" / "fixtures" / case_id
        assert (fixture / "prompt.md").is_file()
        assert (fixture / "plan.md").is_file()


def test_scorer_uses_actual_diff_and_verification(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    source = fixture / "source.py"
    source.write_text("before\n", encoding="utf-8")
    before = score_implementation_evaluation.snapshot(fixture)
    source.write_text("after\n", encoding="utf-8")
    case = {
        "minimum_score": 90,
        "required_changed": ["source.py"],
        "allowed_changed": ["source.py"],
        "preserved": [],
        "verification_commands": ['python -c "print(1)"'],
        "required_report": ["complete"],
        "forbidden_report": [],
        "require_bundle": False,
    }

    result = score_implementation_evaluation.score("Complete", case, fixture, before, fixture / "missing.json")

    assert result["passed"] is True
    assert result["score"] == 100
    assert result["changed_paths"] == ["source.py"]


def test_scorer_hard_fails_scope_and_sentinel_damage(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    sentinel = fixture / "sentinel.txt"
    sentinel.write_text("user\n", encoding="utf-8")
    before = score_implementation_evaluation.snapshot(fixture)
    sentinel.write_text("agent\n", encoding="utf-8")
    (fixture / "extra.txt").write_text("extra\n", encoding="utf-8")
    case = {
        "required_changed": [],
        "allowed_changed": [],
        "preserved": ["sentinel.txt"],
        "verification_commands": [],
        "required_report": [],
        "forbidden_report": [],
        "require_bundle": False,
    }

    result = score_implementation_evaluation.score("Blocked", case, fixture, before, fixture / "missing.json")

    assert "diff:out-of-scope:extra.txt" in result["hard_failures"]
    assert "safety:sentinel-modified:sentinel.txt" in result["hard_failures"]
    assert result["passed"] is False


def test_weights_total_one_hundred() -> None:
    assert sum(score_implementation_evaluation.WEIGHTS.values()) == 100
