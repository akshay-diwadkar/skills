from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_worked_examples_document_valid_finalization_order_and_all_families() -> None:
    text = (
        ROOT / "skills" / "engineering" / "plan-change" / "references" / "worked-examples.md"
    ).read_text(encoding="utf-8")
    order = [
        "prepare_plan.py",
        "without `--require-finalized`",
        "finalize_plan.py",
        "check_plan.py --require-finalized",
    ]
    positions = [text.index(value) for value in order]
    assert positions == sorted(positions)
    for heading in ("Tiny", "Standard", "Security", "Concurrency", "Migration", "ownership", "Fail-closed"):
        assert heading.casefold() in text.casefold()


def test_every_configured_evaluation_has_fixture_and_structured_expectations() -> None:
    evals = ROOT / "tests" / "skills" / "plan-change" / "evals"
    scenarios = json.loads((evals / "v5_scenarios.json").read_text())
    expectations = json.loads((evals / "expectations.json").read_text())
    names = {name for family in scenarios["scenario_families"].values() for name in family}
    assert names == set(expectations)
    assert all((evals / "fixtures" / name / "prompt.md").is_file() for name in names)
    assert all(
        {"grounding", "propagation", "decisions", "implementation", "blueprints", "verification"}
        <= set(expectations[name])
        for name in names
    )
