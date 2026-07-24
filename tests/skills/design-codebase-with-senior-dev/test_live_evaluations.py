import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "design-codebase-with-senior-dev"
sys.path.insert(0, str(DEV_DIR))

import score_design_evaluation  # noqa: E402
from run_live_evaluations import invoke_adapter, run_case, tree_hash  # noqa: E402
from test_check_assessment import assessment  # noqa: E402


def test_adapter_uses_json_stdin_and_stdout(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "import json, sys\n"
        "request = json.load(sys.stdin)\n"
        "print(json.dumps({'assessment_markdown': '# ' + request['case_id']}))\n",
        encoding="utf-8",
    )

    result = invoke_adapter(
        [sys.executable, str(adapter)],
        {"case_id": "case-one", "model_label": "weak", "prompt": "Assess", "repo_root": ".", "skill_path": "."},
        10,
    )

    assert result == "# case-one"


def test_adapter_nonzero_exit_is_infrastructure_failure(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text("raise SystemExit(7)\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="adapter exited 7"):
        invoke_adapter([sys.executable, str(adapter)], {"case_id": "case-one"}, 10)


def test_adapter_malformed_json_is_infrastructure_failure(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text("print('not-json')\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="malformed JSON"):
        invoke_adapter([sys.executable, str(adapter)], {"case_id": "case-one"}, 10)


def test_tree_hash_detects_fixture_mutation(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    source = fixture / "system.py"
    source.write_text("value = 1\n", encoding="utf-8")
    before = tree_hash(fixture)

    source.write_text("value = 2\n", encoding="utf-8")

    assert tree_hash(fixture) != before


def test_run_case_scores_adapter_output_and_writes_artifacts(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    output = tmp_path / "assessment.md"
    output.write_text(assessment("L0"), encoding="utf-8")
    adapter.write_text(
        "import json, pathlib, sys\n"
        "json.load(sys.stdin)\n"
        "print(json.dumps({'assessment_markdown': pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')}))\n",
        encoding="utf-8",
    )
    expectations = json.loads(score_design_evaluation.EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    result = run_case(
        [sys.executable, str(adapter), str(output)],
        "l0-long-file-decoy",
        expectations["l0-long-file-decoy"],
        "weak-model",
        1,
        10,
        tmp_path / "results",
    )

    assert result["score"] == 100
    assert result["hard_failures"] == []
    assert (tmp_path / "results" / "weak-model" / "l0-long-file-decoy" / "run-1.md").is_file()
