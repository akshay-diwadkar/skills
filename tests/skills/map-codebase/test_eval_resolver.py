import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = ROOT / "tests" / "skills" / "map-codebase" / "eval"


def test_legacy_smoke_portfolio_keeps_thirty_cases_per_repository() -> None:
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


def test_committed_legacy_baseline_covers_every_repository() -> None:
    baseline = json.loads((EVAL_DIR / "baseline.json").read_text(encoding="utf-8"))
    assert set(baseline["repositories"]) == {
        "python-small",
        "javascript-small",
        "mixed-config",
        "realistic-large",
    }
    assert 0.0 <= baseline["overall"] <= 1.0
    assert baseline["repositories"]["javascript-small"] >= 0.85


def test_realistic_large_is_preserved_as_homogeneous_scale_evidence() -> None:
    fixture = EVAL_DIR / "repos" / "realistic-large"
    files = [path for path in fixture.rglob("*") if path.is_file()]
    numbered = [
        path
        for path in files
        if path.name.startswith(("component_", "check_component_", "service-"))
    ]
    assert len(files) == 228
    assert len(numbered) == 206
    component = (fixture / "src" / "services" / "component_010.py").read_text(encoding="utf-8")
    assert "from src.services.component_009 import services_value_009" in component
