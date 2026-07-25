"""Regression coverage for evidence-backed task resolution."""

import shlex
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from resolve_task import _fallback_search, resolve_task


def _build(root: Path) -> Path:
    output = root / ".agent" / "knowledge"
    build_knowledge(root, output)
    return output


def _assert_positive_evidence(result: dict) -> None:
    phases = result["phases"] if result["phase"] == "all" else [result]
    for phase in phases:
        for target in phase["targets"]:
            assert target["evidence"]


def _fallback_pattern(command: str) -> str:
    return shlex.split(command)[-1]


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


def test_configuration_fallback_uses_unescaped_assignment_pattern(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.example]\nexisting-key = 1\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Change timeout in pyproject.toml", output)

    assert result["targets"][0]["role"] == "configuration"
    assert result["targets"][0]["start_line"] is None
    assert len(result["fallback_searches"]) == 1
    pattern = _fallback_pattern(result["fallback_searches"][0])
    assert pattern == r"timeout\s*[:=]"
    assert r"\\s\*" not in pattern


def test_ownerless_configuration_uses_key_shaped_fallbacks(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Set frobnicator quorum-size in project configuration", output, phase="all")

    assert result["task_intent"]["primary_role"] == "configuration"
    assert all(phase["targets"] == [] for phase in result["phases"])
    assert result["confidence"]["level"] == "low"
    assert result["confidence"]["score"] == 0
    pattern = _fallback_pattern(result["fallback_searches"][0])
    assert pattern == r"quorum\-size\s*[:=]"
    assert r"\\s\*" not in pattern


def test_ownerless_configuration_prefers_dotted_key_fallback(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Set tool.frobnicator.timeout in configuration", output)

    assert _fallback_pattern(result["fallback_searches"][0]) == r"tool\.frobnicator\.timeout\s*[:=]"


def test_source_fallback_remains_whole_token(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Implement frobnicator reconciliation", output)

    patterns = [_fallback_pattern(command) for command in result["fallback_searches"]]
    assert r"\bfrobnicator\b" in patterns
    assert all(r"\s*[:=]" not in pattern for pattern in patterns)


def test_custom_output_is_excluded_from_configuration_fallbacks(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = tmp_path / ".cache" / "custom-knowledge"
    build_knowledge(tmp_path, output)

    result = resolve_task(tmp_path, "Set frobnicator quorum-size in project configuration", output)

    assert result["fallback_searches"]
    assert all("!.cache/custom-knowledge/**" in shlex.split(command) for command in result["fallback_searches"])
    assert all("!.agent/knowledge/**" not in shlex.split(command) for command in result["fallback_searches"])


def test_fallback_search_escapes_regex_sensitive_literal() -> None:
    command = _fallback_search(".agent/knowledge", "frob.nicator")

    assert _fallback_pattern(command) == r"\bfrob\.nicator\b"
    assert shlex.split(command) == ["rg", "-n", "--glob", "!.agent/knowledge/**", "--", r"\bfrob\.nicator\b"]


def test_ownerless_configuration_fallbacks_are_bounded_and_deterministic(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    first = resolve_task(tmp_path, "Set frobnicator quorum-size in project configuration", output, phase="all")
    second = resolve_task(tmp_path, "Set frobnicator quorum-size in project configuration", output, phase="all")

    assert first["fallback_searches"] == second["fallback_searches"]
    assert len(first["fallback_searches"]) <= 3
    assert len(first["fallback_searches"]) == len(set(first["fallback_searches"]))
    assert all(phase["targets"] == [] for phase in first["phases"][1:])


def test_weak_real_match_keeps_only_positive_evidence_targets(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "frobnicator.py").write_text("def handle(): return True\n", encoding="utf-8")
    output = _build(tmp_path)

    result = resolve_task(tmp_path, "Fix frobnicator", output, phase="all")

    assert result["phases"][0]["targets"][0]["path"] == "src/frobnicator.py"
    assert result["confidence"]["level"] == "medium"
    _assert_positive_evidence(result)
