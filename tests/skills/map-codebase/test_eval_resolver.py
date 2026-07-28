import importlib.util
import json
import os
from collections import Counter
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
EVAL_SCRIPT = ROOT / "skills" / "engineering" / "map-codebase" / "scripts" / "eval_resolver.py"
EVAL_DIR = ROOT / "tests" / "skills" / "map-codebase" / "eval"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("eval_resolver", EVAL_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_manifest_has_thirty_cases_per_repository() -> None:
    cases = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))
    assert Counter(case["repo"] for case in cases) == {
        "python-small": 30,
        "javascript-small": 30,
        "mixed-config": 30,
        "realistic-large": 30,
    }
    for case in cases:
        assert set(case) in (
            {"repo", "task", "role", "path"},
            {"repo", "task", "role", "path", "symbol"},
        )
        assert case["role"] in {"source", "test", "configuration"}
        assert (EVAL_DIR / "repos" / case["repo"] / case["path"]).is_file()


def test_metric_calculation_counts_owner_misses_by_role() -> None:
    module = _module()
    metrics = module.calculate_metrics(
        [
            {"repo": "sample", "role": "source", "predicted_role": "source", "correct": True},
            {"repo": "sample", "role": "source", "predicted_role": "source", "correct": False},
            {"repo": "sample", "role": "test", "predicted_role": None, "correct": False},
        ]
    )
    assert metrics["hit_at_1"] == 1 / 3
    assert metrics["roles"]["source"]["precision"] == 0.5
    assert metrics["roles"]["source"]["recall"] == 0.5
    assert metrics["roles"]["test"]["recall"] == 0.0


def test_committed_baseline_covers_every_fixture_repository() -> None:
    baseline = json.loads((EVAL_DIR / "baseline.json").read_text(encoding="utf-8"))
    assert set(baseline["repositories"]) == {
        "python-small",
        "javascript-small",
        "mixed-config",
        "realistic-large",
    }
    assert 0.0 <= baseline["overall"] <= 1.0


def test_realistic_fixture_has_hundreds_of_files_and_cross_module_imports() -> None:
    fixture = EVAL_DIR / "repos" / "realistic-large"
    assert len([path for path in fixture.rglob("*") if path.is_file()]) >= 200
    component = (fixture / "src" / "services" / "component_010.py").read_text(encoding="utf-8")
    assert "from src.services.component_009 import services_value_009" in component


def test_retrieval_metrics_credit_savings_only_to_correct_results() -> None:
    module = _module()
    metrics = module.calculate_retrieval_metrics(
        [
            {
                "repo": "sample",
                "correct": True,
                "resolver_tokens": 10,
                "grep_tokens": 100,
                "resolver_characters": 40,
                "grep_characters": 400,
            },
            {
                "repo": "sample",
                "correct": False,
                "resolver_tokens": 1,
                "grep_tokens": 100,
                "resolver_characters": 4,
                "grep_characters": 400,
            },
        ]
    )
    assert metrics["sample"]["correct"]["token_savings"] == 0.9
    assert metrics["sample"]["incorrect"]["token_savings"] == 0.0
    assert metrics["sample"]["incorrect"]["character_savings"] == 0.0


def test_quality_check_does_not_reuse_stale_bytecode(tmp_path: Path) -> None:
    module = _module()
    subject = tmp_path / "subject.py"
    subject.write_text("VALUE = 1\n", encoding="utf-8")
    timestamp = subject.stat().st_mtime_ns

    assert module._run_check(
        tmp_path,
        ["{python}", "-c", "import subject; assert subject.VALUE == 1"],
    )
    assert not (tmp_path / "__pycache__").exists()

    subject.write_text("VALUE = 2\n", encoding="utf-8")
    os.utime(subject, ns=(timestamp, timestamp))
    assert module._run_check(
        tmp_path,
        ["{python}", "-c", "import subject; assert subject.VALUE == 2"],
    )
