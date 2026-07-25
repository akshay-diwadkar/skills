"""Regression coverage for evidence-backed task resolution."""

import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import resolve_task


def _build(root: Path) -> Path:
    output = root / ".agent" / "knowledge"
    build_knowledge(root, output)
    return output


def _assert_positive_evidence(result: dict) -> None:
    phases = result["phases"] if result["phase"] == "all" else [result]
    for phase in phases:
        for target in phase["targets"]:
            assert target["evidence"]


def test_no_match_returns_empty_resolution_and_safe_fallback(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    (tmp_path / "tests" / "test_service.py").write_text("def test_service(): assert True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Fix frobnicator", output, phase="all")

    assert result["confidence"] == {
        "level": "low",
        "score": 0,
        "reasons": ["no indexed owner matched the task terms"],
        "uncertainties": ["run the targeted fallback search against authoritative source"],
    }
    assert all(phase["targets"] == [] for phase in result["phases"])
    assert result["fallback_searches"] == ["rg -n --glob '!.agent/knowledge/**' -- '\\bfrobnicator\\b'"]
    assert "role_fallback" not in str(result)
    _assert_positive_evidence(result)


def test_no_match_does_not_fabricate_test_targets(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Fix frobnicator", output, phase=2)

    assert result["targets"] == []


def test_no_match_does_not_fabricate_configuration_targets(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Change frobnicator configuration", output)

    assert result["targets"] == []
    assert result["confidence"]["level"] == "low"


def test_weak_real_match_keeps_only_positive_evidence_targets(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "frobnicator.py").write_text("def handle(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Fix frobnicator", output, phase="all")

    assert result["phases"][0]["targets"][0]["path"] == "src/frobnicator.py"
    assert result["confidence"]["level"] == "medium"
    _assert_positive_evidence(result)
