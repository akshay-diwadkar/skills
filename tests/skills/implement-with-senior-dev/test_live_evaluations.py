import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "implement-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))

SPEC = importlib.util.spec_from_file_location(
    "implement_run_live_evaluations",
    DEV_DIR / "run_live_evaluations.py",
)
assert SPEC is not None
live_runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = live_runner
SPEC.loader.exec_module(live_runner)
invoke_adapter = live_runner.invoke_adapter
summarize = live_runner.summarize
tree_hash = live_runner.tree_hash


def test_adapter_uses_json_stdin_and_stdout(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "import json, sys\n"
        "request = json.load(sys.stdin)\n"
        "print(json.dumps({'implementation_report_markdown': request['prompt']}))\n",
        encoding="utf-8",
    )

    report = invoke_adapter([sys.executable, str(adapter)], {"prompt": "implemented"}, 10, tmp_path)

    assert report == "implemented"


def test_tree_hash_detects_source_fixture_mutation(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_text("before\n", encoding="utf-8")
    before = tree_hash(tmp_path)
    path.write_text("after\n", encoding="utf-8")

    assert tree_hash(tmp_path) != before


def test_summary_requires_median_ninety_minimum_eighty_and_no_hard_failures() -> None:
    results = [
        {"model_label": "weak", "score": 100, "hard_failures": []},
        {"model_label": "weak", "score": 90, "hard_failures": []},
        {"model_label": "weak", "score": 80, "hard_failures": []},
        {"model_label": "bad", "score": 100, "hard_failures": ["scope"]},
    ]

    passed, summaries = summarize(results, ["weak", "bad"])

    assert passed is False
    assert summaries["weak"] == {
        "median_score": 90.0,
        "minimum_score": 80.0,
        "hard_failures": [],
        "runs": 3,
        "passed": True,
    }
    assert summaries["bad"]["passed"] is False


def test_adapter_rejects_malformed_response(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text("print('not json')\n", encoding="utf-8")

    try:
        invoke_adapter([sys.executable, str(adapter)], {"prompt": "x"}, 10, tmp_path)
    except RuntimeError as exc:
        assert "malformed JSON" in str(exc)
    else:
        raise AssertionError("malformed adapter response was accepted")


def test_expectations_are_valid_json() -> None:
    expectations = json.loads((DEV_DIR / "evals" / "expectations.json").read_text(encoding="utf-8"))

    assert len(expectations) == 10
