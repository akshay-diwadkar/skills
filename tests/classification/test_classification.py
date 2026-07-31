from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tools.classification.runtime import classify, recommendation_sha256, verify_override

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((Path(__file__).parent / "fixtures" / "cases.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "tools" / "classification" / "result.schema.json").read_text(encoding="utf-8"))


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text(
        "def parse_name(value: str) -> str:\n    return value.strip()\n",
        encoding="utf-8",
    )
    return repo


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case['kind']}-{case['class']}")
def test_deterministic_classification_fixture(case: dict[str, object], repository: Path, tmp_path: Path) -> None:
    source = tmp_path / "request.txt"
    source.write_text(str(case["source"]), encoding="utf-8")
    first = classify(str(case["kind"]), repository, source)
    second = classify(str(case["kind"]), repository, source)
    assert first == second
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(
        second, sort_keys=True, separators=(",", ":")
    )
    jsonschema.validate(first, SCHEMA)
    if "expected_status" in case:
        assert first["recommendation"]["status"] == case["expected_status"]
    values = first["recommendation"]["values"]
    for key, value in dict(case.get("expected", {})).items():
        assert values[key] == value


def test_override_requires_current_non_comment_source(repository: Path, tmp_path: Path) -> None:
    request = tmp_path / "request.md"
    request.write_text("Refactor src/app.py function parse_name preserving behavior.", encoding="utf-8")
    result = classify("plan-change", repository, request)
    source = repository / "src" / "app.py"
    lines = source.read_text(encoding="utf-8").splitlines()
    excerpt = lines[0].encode("utf-8")
    import hashlib

    payload = {
        "recommendation_sha256": recommendation_sha256(result),
        "overrides": {"tier": "standard"},
        "evidence": [{
            "field": "tier",
            "source_kind": "repository-source",
            "path": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "start_line": 1,
            "end_line": 1,
            "excerpt_sha256": hashlib.sha256(excerpt).hexdigest(),
            "observation": "The named function is a shared typed interface.",
        }],
    }
    override = tmp_path / "override.json"
    override.write_text(json.dumps(payload), encoding="utf-8")
    assert verify_override(result, override, repository, request)["tier"] == "standard"
    source.write_text("# comment only\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        verify_override(result, override, repository, request)


def test_override_rejects_generated_and_escaping_evidence(repository: Path, tmp_path: Path) -> None:
    request = tmp_path / "request.md"
    request.write_text("Refactor src/app.py function parse_name preserving behavior.", encoding="utf-8")
    result = classify("plan-change", repository, request)
    outside = tmp_path / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")
    import hashlib

    payload = {
        "recommendation_sha256": recommendation_sha256(result),
        "overrides": {"tier": "standard"},
        "evidence": [{
            "field": "tier",
            "source_kind": "repository-source",
            "path": str(outside),
            "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            "start_line": 1,
            "end_line": 1,
            "excerpt_sha256": hashlib.sha256(b"value = 1").hexdigest(),
            "observation": "Outside claim.",
        }],
    }
    override = tmp_path / "override.json"
    override.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        verify_override(result, override, repository, request)
