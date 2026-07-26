from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import Diagnostic, Record, _fact_fields  # noqa: E402


def _record(kind: str, path: str, lines: str, anchor: str, **fields: str) -> Record:
    return Record(
        "F-1",
        {
            "kind": kind,
            "path": path,
            "lines": lines,
            "anchor": anchor,
            "excerpt-sha256": "0" * 64,
            "file-sha256": "0" * 64,
            "observation": "structured test evidence",
            **fields,
        },
        1,
        "Evidence Ledger",
    )


def _check(tmp_path: Path, fact: Record) -> list[str]:
    path = tmp_path / fact.fields["path"]
    source = path.read_text(encoding="utf-8")
    start, end = map(int, fact.fields["lines"].split("-"))
    excerpt = "\n".join(source.splitlines()[start - 1 : end]) + "\n"
    diagnostics: list[Diagnostic] = []
    _fact_fields(diagnostics, fact, excerpt, source, path, tmp_path)
    return [item.code for item in diagnostics]


def test_nested_positional_keyword_only_async_signature(tmp_path: Path) -> None:
    source = "async def run(items: tuple[int, int] = (1, 2), /, *, flag: bool = True) -> str:\n    return str(items)\n"
    (tmp_path / "api.py").write_text(source)
    fact = _record(
        "function-signature",
        "api.py",
        "1-1",
        "run",
        parameters="items: tuple[int, int] = (1, 2), /, *, flag: bool = True",
        returns="str",
        **{"async": "true"},
    )
    assert _check(tmp_path, fact) == []


def test_qualified_call_must_be_inside_cited_range(tmp_path: Path) -> None:
    (tmp_path / "calls.py").write_text("def caller():\n    return client.api.send()\n")
    valid = _record("call-edge", "calls.py", "1-2", "caller", caller="caller", callee="client.api.send")
    assert _check(tmp_path, valid) == []
    outside = _record("call-edge", "calls.py", "1-1", "caller", caller="caller", callee="client.api.send")
    assert "fact.structured" in _check(tmp_path, outside)


def test_classes_branches_and_errors_are_ast_verified(tmp_path: Path) -> None:
    source = "class Child(Base):\n    pass\n\ndef parse(value):\n    if not value:\n        raise ValueError('blank')\n"
    (tmp_path / "model.py").write_text(source)
    assert _check(tmp_path, _record("class-signature", "model.py", "1-1", "Child", bases="Base")) == []
    assert _check(tmp_path, _record("branch", "model.py", "5-5", "not value", condition="not value")) == []
    assert _check(tmp_path, _record("error", "model.py", "6-6", "ValueError", error="ValueError('blank')")) == []


def test_json_schema_and_config_claims_are_structural(tmp_path: Path) -> None:
    (tmp_path / "schema.json").write_text('{"properties":{"name":{"type":"string"},"age":{"type":"integer"}}}\n')
    schema = _record("schema-shape", "schema.json", "1-1", "properties", fields="name, age")
    assert _check(tmp_path, schema) == []
    (tmp_path / "config.json").write_text('{"service":{"timeout":30}}\n')
    config = _record("config-key", "config.json", "1-1", "timeout", key="service.timeout", value="30")
    assert _check(tmp_path, config) == []
