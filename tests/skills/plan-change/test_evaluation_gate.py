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


def _run(
    attempt: int,
    *,
    downstream: str = "not-applicable",
    model: str = "terra-medium",
    scenario: str = "case-one",
    score: int = 100,
    dimension: int = 100,
    hard_failures: list[str] | None = None,
    repository_mutation: bool = False,
) -> dict[str, object]:
    return {
        "score": score,
        "dimension_scores": {name: dimension for name in MODULE.WEIGHTS},
        "hard_failures": hard_failures or [],
        "family": "tiny",
        "scenario": scenario,
        "model_label": model,
        "attempt": attempt,
        "downstream_status": downstream,
        "repository_mutation": repository_mutation,
    }


def test_release_gate_requires_three_successes_per_model_scenario() -> None:
    assert MODULE.release_gate([_run(1), _run(2), _run(3)]) == []
    assert any("pair_runs" in failure for failure in MODULE.release_gate([_run(1), _run(2)]))


def test_not_applicable_downstream_is_excluded_but_failure_blocks() -> None:
    assert MODULE.release_gate([_run(1), _run(2), _run(3)]) == []
    failed = [_run(1), _run(2), _run(3, downstream="failed")]
    assert any("downstream" in failure for failure in MODULE.release_gate(failed))


def test_every_gate_is_isolated_per_model_scenario_pair() -> None:
    strong = [_run(attempt, model="strong", scenario="healthy") for attempt in (1, 2, 3)]
    cases = {
        "median": [_run(1, model="weak", scenario="median", score=96), _run(2, model="weak", scenario="median", score=97), _run(3, model="weak", scenario="median")],
        "minimum": [_run(1, model="weak", scenario="minimum", score=94), _run(2, model="weak", scenario="minimum"), _run(3, model="weak", scenario="minimum")],
        "dimension": [_run(1, model="weak", scenario="dimension", dimension=89), _run(2, model="weak", scenario="dimension"), _run(3, model="weak", scenario="dimension")],
        "hard_failures": [_run(1, model="weak", scenario="hard", hard_failures=["bad"]), _run(2, model="weak", scenario="hard"), _run(3, model="weak", scenario="hard")],
        "repository_mutation": [_run(1, model="weak", scenario="mutation", repository_mutation=True), _run(2, model="weak", scenario="mutation"), _run(3, model="weak", scenario="mutation")],
    }
    for expected, weak in cases.items():
        failures = MODULE.release_gate(strong + weak)
        assert any(expected in failure and "weak/" in failure for failure in failures)
        assert not any("strong/healthy" in failure for failure in failures)


def test_scoring_uses_parsed_record_families_not_raw_substrings() -> None:
    text = render_scaffold("tiny", "bug-fix", []) + "\nmagic-decision-token\n"
    expectations = {"decisions": {"terms": ["magic-decision-token"]}}
    _score, dimensions, missing = MODULE.score_expectations(text, expectations)
    assert dimensions["decisions"] < 100
    assert "decisions:term=magic-decision-token" in missing
    text = text.replace("selected: name", "selected: magic-decision-token name")
    _score, dimensions, _missing = MODULE.score_expectations(text, expectations)
    assert dimensions["decisions"] == 100
