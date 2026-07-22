import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "tests" / "plan-with-senior-dev"
RUNNER_PATH = DEV_DIR / "run_live_evaluations.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("plan_with_senior_dev_live_evaluations", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)

invoke_adapter = RUNNER.invoke_adapter
run_case = RUNNER.run_case
summarize = RUNNER.summarize
tree_hash = RUNNER.tree_hash


def test_adapter_uses_json_stdin_and_stdout(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "import json, sys\n"
        "request = json.load(sys.stdin)\n"
        "print(json.dumps({'plan_markdown': '# ' + request['case_id']}))\n",
        encoding="utf-8",
    )
    result = invoke_adapter([sys.executable, str(adapter)], {"case_id": "case-one"}, 10)
    assert result == "# case-one"


def test_adapter_failures_are_infrastructure_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("print('not-json')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="malformed JSON"):
        invoke_adapter([sys.executable, str(bad)], {"case_id": "case-one"}, 10)


def test_tree_hash_detects_fixture_mutation(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_text("before\n", encoding="utf-8")
    before = tree_hash(tmp_path)
    path.write_text("after\n", encoding="utf-8")
    assert tree_hash(tmp_path) != before


def test_summary_requires_receipt_clean_scores_and_full_blueprints() -> None:
    passing = [
        {"model_label": "weak", "score": score, "hard_failures": [], "dimension_scores": {"blueprint": 100}}
        for score in (80, 90, 100)
    ]
    failed_blueprint = [
        {"model_label": "weak", "score": 100, "hard_failures": [], "dimension_scores": {"blueprint": 50}}
    ]
    passed, summaries = summarize(passing, ["weak"])
    failed, _ = summarize(failed_blueprint, ["weak"])
    assert passed is True
    assert summaries["weak"]["median_score"] == 90
    assert summaries["weak"]["minimum_score"] == 80
    assert failed is False


def test_expectations_include_blueprint_dimension() -> None:
    expectations = json.loads((DEV_DIR / "evals" / "expectations.json").read_text(encoding="utf-8"))
    assert len(expectations) == 6
    assert all("blueprint" in case for case in expectations.values())


def test_run_case_scores_output_and_preserves_raw_artifacts(tmp_path: Path) -> None:
    examples = REPO_ROOT / "plan-with-senior-dev" / "references" / "worked-examples.md"
    plan = examples.read_text(encoding="utf-8").split("```plan\n", 1)[1].split("\n```", 1)[0]
    output = tmp_path / "plan.md"
    output.write_text(plan, encoding="utf-8")
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "import json, pathlib, sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'plan_markdown': pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')}))\n",
        encoding="utf-8",
    )
    expectations = json.loads((DEV_DIR / "evals" / "expectations.json").read_text(encoding="utf-8"))
    result = run_case(
        [sys.executable, str(adapter), str(output)],
        "tiny-boundary-bug",
        expectations["tiny-boundary-bug"],
        "weak",
        1,
        10,
        tmp_path / "results",
    )
    assert result["score"] == 100
    assert result["hard_failures"] == []
    assert (tmp_path / "results" / "weak" / "tiny-boundary-bug" / "run-1.md").is_file()
