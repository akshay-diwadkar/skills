from __future__ import annotations

import importlib.util
from pathlib import Path

PATH = Path(__file__).with_name("score_plan_evaluation.py")
SPEC = importlib.util.spec_from_file_location("score_plan_evaluation", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_behavioral_score_requires_each_dimension() -> None:
    score, dimensions, missing = MODULE.score_expectations(
        "src/a.py caller decision CH-1 test T-1", {"grounding": ["src/a.py"], "propagation": ["caller"], "decisions": ["decision"], "implementation": ["CH-1"], "verification": ["T-1"]}
    )
    assert score == 100
    assert all(value == 100 for value in dimensions.values())
    assert missing == []


def test_98_median_and_95_floor_are_release_gates() -> None:
    runs = [{"score": 98, "dimension_scores": {name: 100 for name in MODULE.WEIGHTS}, "hard_failures": [], "family": "tiny", "downstream_passed": True} for _ in range(3)]
    assert MODULE.release_gate(runs) == []
    runs[0]["score"] = 94
    assert "evaluation.minimum: every run minimum is 95" in MODULE.release_gate(runs)
