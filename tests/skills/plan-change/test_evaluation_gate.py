from __future__ import annotations

import importlib.util
from pathlib import Path

PATH = Path(__file__).with_name("score_plan_evaluation.py")
SPEC = importlib.util.spec_from_file_location("score_plan_evaluation", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_blueprint_floor_is_a_release_gate() -> None:
    runs = [{"score": 96, "blueprint_score": 89, "hard_failures": 0} for _ in range(3)]
    assert MODULE.release_gate(runs) == ["evaluation.blueprint: every standard/high-risk blueprint minimum is 90"]
