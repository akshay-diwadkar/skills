import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = REPO_ROOT / "tests" / "optimize-codebase-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))

import score_optimization_evaluation  # noqa: E402
from report_factory import valid_report  # noqa: E402


SPEC = importlib.util.spec_from_file_location(
    "optimize_run_live_evaluations",
    DEV_DIR / "run_live_evaluations.py",
)
assert SPEC is not None
live_runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = live_runner
SPEC.loader.exec_module(live_runner)
invoke_adapter = live_runner.invoke_adapter
run_case = live_runner.run_case
tree_hash = live_runner.tree_hash
summarize_results = live_runner.summarize_results


def test_adapter_uses_json_stdin_and_stdout(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "import json, sys\n"
        "request = json.load(sys.stdin)\n"
        "print(json.dumps({'optimization_markdown': '# ' + request['case_id']}))\n",
        encoding="utf-8",
    )

    result = invoke_adapter(
        [sys.executable, str(adapter)],
        {"case_id": "case-one", "model_label": "weak", "prompt": "Optimize", "repo_root": ".", "skill_path": "."},
        10,
    )

    assert result == "# case-one"


def test_adapter_failures_are_infrastructure_errors(tmp_path: Path) -> None:
    nonzero = tmp_path / "nonzero.py"
    nonzero.write_text("raise SystemExit(7)\n", encoding="utf-8")
    malformed = tmp_path / "malformed.py"
    malformed.write_text("print('not-json')\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="adapter exited 7"):
        invoke_adapter([sys.executable, str(nonzero)], {"case_id": "case-one"}, 10)
    with pytest.raises(RuntimeError, match="malformed JSON"):
        invoke_adapter([sys.executable, str(malformed)], {"case_id": "case-one"}, 10)


def test_tree_hash_detects_fixture_mutation(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    source = fixture / "system.py"
    source.write_text("value = 1\n", encoding="utf-8")
    before = tree_hash(fixture)
    source.write_text("value = 2\n", encoding="utf-8")

    assert tree_hash(fixture) != before


def test_run_case_scores_output_and_writes_artifacts(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    output = tmp_path / "optimization.md"
    expectations = json.loads(score_optimization_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    case = expectations["hot-path-decoy"]
    output.write_text(valid_report(note=case["acceptance_note"]), encoding="utf-8")
    adapter.write_text(
        "import json, pathlib, sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'optimization_markdown': pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')}))\n",
        encoding="utf-8",
    )

    result = run_case(
        [sys.executable, str(adapter), str(output)],
        "hot-path-decoy",
        case,
        "weak-model",
        1,
        10,
        tmp_path / "results",
    )

    assert result["score"] == 100
    assert result["hard_failures"] == []
    assert (tmp_path / "results" / "weak-model" / "hot-path-decoy" / "run-1.md").is_file()


def test_summary_requires_median_ninety_minimum_eighty_and_no_hard_failures() -> None:
    passing: list[dict[str, Any]] = [
        {"model_label": "weak", "score": score, "hard_failures": []}
        for score in (80, 90, 100)
    ]
    failing: list[dict[str, Any]] = [
        {"model_label": "weak", "score": 100, "hard_failures": []},
        {"model_label": "weak", "score": 79, "hard_failures": []},
        {"model_label": "weak", "score": 100, "hard_failures": ["fixture:mutated"]},
    ]

    passed, summaries = summarize_results(passing, ["weak"])
    failed, failing_summaries = summarize_results(failing, ["weak"])

    assert passed is True
    assert summaries["weak"]["median_score"] == 90
    assert summaries["weak"]["minimum_score"] == 80
    assert failed is False
    assert failing_summaries["weak"]["hard_failures"] == ["fixture:mutated"]
