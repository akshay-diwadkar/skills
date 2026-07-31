from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEV = ROOT / "tests" / "skills" / "design-codebase"
sys.path.insert(0, str(DEV))

from run_live_evaluations import evaluate  # noqa: E402
from score_design_evaluation import score_expectations  # noqa: E402

EVALS = DEV / "evals"
FIXTURES = EVALS / "fixtures"


def test_design_fixture_inventory_is_complete_and_groundable() -> None:
    expectations = json.loads((EVALS / "expectations.json").read_text(encoding="utf-8"))
    expected_names = {
        "premature-abstraction",
        "shallow-wrapper",
        "genuine-seam",
        "wrong-ownership",
        "high-propagation",
        "poor-locality",
        "consolidation",
    }
    assert set(expectations) == expected_names
    assert {path.name for path in FIXTURES.iterdir() if path.is_dir()} == expected_names
    for name, expected in expectations.items():
        fixture = FIXTURES / name
        prompt = (fixture / "prompt.md").read_text(encoding="utf-8")
        evidence_files = [path for path in fixture.rglob("*.py") if path.is_file()]
        assert "design handoff" in prompt.casefold() or "design-codebase" in prompt.casefold()
        assert "implement" not in prompt.casefold() or "do not plan or implement" in prompt.casefold()
        assert len(evidence_files) >= 2
        assert 1 <= len(expected["required_concepts"]) <= 2
        assert expected["outcome_any"]
        assert "implementation plan" in expected["forbidden"]


def test_scorer_requires_relevant_vocabulary_without_requiring_all_terms() -> None:
    expected = {
        "required_concepts": ["deletion test", "depth"],
        "outcome_any": ["remove wrapper"],
        "forbidden": ["implementation plan"],
    }
    passing = score_expectations(
        "The wrapper fails the deletion test and has no depth, so remove wrapper. [E-2]",
        expected,
    )
    assert passing == {
        "score": 100.0,
        "missing_concepts": [],
        "outcome_matched": True,
        "forbidden": [],
    }
    assert score_expectations("Remove wrapper. [E-2]", expected)["score"] == 60.0


def test_provider_neutral_runner_isolates_fixture_and_detects_mutation(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "import json, pathlib, sys\n"
        "request = json.load(sys.stdin)\n"
        "pathlib.Path(request['repo_root'], 'mutation.txt').write_text('changed', encoding='utf-8')\n"
        "print(json.dumps({'handoff_markdown': '# invalid'}))\n",
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    report = evaluate(
        [sys.executable, str(adapter)],
        output,
        scenarios=["premature-abstraction"],
        model_label="weak-agent",
    )
    run = report["runs"][0]
    assert run["repository_mutation"] is True
    assert "repository-mutation" in run["hard_failures"]
    assert any(item.startswith("contract:") for item in run["hard_failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["contract_version"] == 1
