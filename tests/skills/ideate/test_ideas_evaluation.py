from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IDEATE_TEST_DIR = ROOT / "tests" / "skills" / "ideate"
EVAL_DIR = IDEATE_TEST_DIR / "evals"

sys.path.insert(0, str(IDEATE_TEST_DIR))
sys.path.insert(0, str(EVAL_DIR))

from score_ideate_evaluation import score_ideas_draft  # type: ignore[import-not-found] # noqa: E402


def test_eval_harness_scoring_valid_draft(tmp_path: Path) -> None:
    from test_ideas_contract import _valid_body  # type: ignore[import-not-found]
    draft = tmp_path / "ideas.md"
    draft.write_text(_valid_body(), encoding="utf-8")
    results = score_ideas_draft(draft)
    assert results["valid"] is True
    assert results["score_pct"] == 100.0
    assert results["passed_dimensions"] == 12


def test_eval_harness_scoring_valid_full_fixture() -> None:
    fixture = EVAL_DIR / "fixtures" / "valid_full.md"
    results = score_ideas_draft(fixture)
    assert results["valid"] is True
    assert results["score_pct"] == 100.0
    assert results["passed_dimensions"] == 12


def test_eval_harness_scoring_missing_experiment_subfields_fixture() -> None:
    fixture = EVAL_DIR / "fixtures" / "missing_experiment_subfields.md"
    results = score_ideas_draft(fixture)
    assert results["valid"] is False
    assert results["checks"]["8_experiment_decisiveness"] is False


def test_eval_harness_scoring_empty_section6_fixture() -> None:
    fixture = EVAL_DIR / "fixtures" / "empty_section6.md"
    results = score_ideas_draft(fixture)
    assert results["valid"] is False
    assert results["checks"]["9_handling_of_contradictions"] is False


def test_eval_harness_scoring_weak_fixture() -> None:
    weak_draft = EVAL_DIR / "fixtures" / "structurally_valid_weak.md"
    results = score_ideas_draft(weak_draft)
    assert results["valid"] is False
    assert results["checks"]["5_lack_of_duplication"] is False
    assert results["score_pct"] < 100.0
