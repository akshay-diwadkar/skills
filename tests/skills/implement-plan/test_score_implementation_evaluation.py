from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCORER_PATH = ROOT / "tests" / "skills" / "implement-plan" / "score_implementation_evaluation.py"
SPEC = importlib.util.spec_from_file_location("score_implementation_evaluation_tested", SCORER_PATH)
assert SPEC and SPEC.loader
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def _case() -> dict[str, object]:
    return {
        "minimum_score": 90,
        "required_changed": [],
        "allowed_changed": [],
        "verification_commands": [],
        "require_bundle": False,
        "required_structural_checks": [
            {
                "id": "signature",
                "type": "python-function-signature",
                "path": "src/service.py",
                "name": "parse_value",
                "parameters": ["value: str"],
                "returns": "int",
            },
            {
                "id": "exceptions",
                "type": "python-no-generic-except",
                "paths": ["src/service.py"],
            },
        ],
    }


def test_structural_checks_contribute_fifteen_points_when_they_pass(tmp_path: Path) -> None:
    source = tmp_path / "src" / "service.py"
    source.parent.mkdir()
    source.write_text("def parse_value(value: str) -> int:\n    return int(value)\n", encoding="utf-8")
    before = SCORER.snapshot(tmp_path)
    result = SCORER.score("", _case(), tmp_path, before, tmp_path / "bundle.json")
    assert result["passed"] is True
    assert result["score"] == 100
    assert result["dimension_scores"]["structural_quality"] == 100


def test_signature_mismatch_is_a_hard_structural_failure(tmp_path: Path) -> None:
    source = tmp_path / "src" / "service.py"
    source.parent.mkdir()
    source.write_text("def parse_value(value: object) -> int:\n    return int(value)\n", encoding="utf-8")
    before = SCORER.snapshot(tmp_path)
    result = SCORER.score("", _case(), tmp_path, before, tmp_path / "bundle.json")
    assert result["passed"] is False
    assert result["score"] == 85
    assert result["dimension_scores"]["structural_quality"] == 0
    assert any(item.startswith("structural:signature:") for item in result["hard_failures"])


def test_bare_and_generic_exception_handlers_fail_structurally(tmp_path: Path) -> None:
    source = tmp_path / "src" / "service.py"
    source.parent.mkdir()
    source.write_text(
        "def parse_value(value: str) -> int:\n"
        "    try:\n"
        "        return int(value)\n"
        "    except Exception:\n"
        "        return 0\n",
        encoding="utf-8",
    )
    before = SCORER.snapshot(tmp_path)
    result = SCORER.score("", _case(), tmp_path, before, tmp_path / "bundle.json")
    assert result["passed"] is False
    assert any(item.startswith("structural:exceptions:") for item in result["hard_failures"])
