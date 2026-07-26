from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_contract import render_scaffold  # noqa: E402

PATH = Path(__file__).with_name("score_plan_evaluation.py")
SPEC = importlib.util.spec_from_file_location("score_plan_evaluation", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _run(attempt: int, *, downstream: str = "not-applicable") -> dict[str, object]:
    return {
        "score": 100,
        "dimension_scores": {name: 100 for name in MODULE.WEIGHTS},
        "hard_failures": [],
        "family": "tiny",
        "scenario": "case-one",
        "model_label": "terra-medium",
        "attempt": attempt,
        "downstream_status": downstream,
    }


def test_release_gate_requires_three_successes_per_model_scenario() -> None:
    assert MODULE.release_gate([_run(1), _run(2), _run(3)]) == []
    assert any("pair_runs" in failure for failure in MODULE.release_gate([_run(1), _run(2)]))


def test_not_applicable_downstream_is_excluded_but_failure_blocks() -> None:
    assert MODULE.release_gate([_run(1), _run(2), _run(3)]) == []
    failed = [_run(1), _run(2), _run(3, downstream="failed")]
    assert any("downstream" in failure for failure in MODULE.release_gate(failed))


def test_scoring_uses_parsed_record_families_not_raw_substrings() -> None:
    text = render_scaffold("tiny", "bug-fix", []) + "\nmagic-decision-token\n"
    expectations = {"decisions": {"terms": ["magic-decision-token"]}}
    _score, dimensions, missing = MODULE.score_expectations(text, expectations)
    assert dimensions["decisions"] < 100
    assert "decisions:term=magic-decision-token" in missing
    text = text.replace("selected: name", "selected: magic-decision-token name")
    _score, dimensions, _missing = MODULE.score_expectations(text, expectations)
    assert dimensions["decisions"] == 100
