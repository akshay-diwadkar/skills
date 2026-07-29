from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import plan_runtime  # noqa: E402
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


@pytest.mark.parametrize(
    ("path", "source", "parameters", "returns", "bases", "branch", "error"),
    [
        (
            "api.ts",
            "export async function load(id: string): Promise<Result> {\n"
            "  if (!id) throw new Error(\"missing\");\n"
            "  client.api.send(id);\n"
            "  state.count += 1;\n"
            "}\n"
            "export class Child extends Base implements Runner {}\n",
            "id: string",
            "Promise<Result>",
            "extends Base implements Runner",
            "!id",
            'new Error("missing")',
        ),
        (
            "api.js",
            "export async function load(id) {\n"
            "  if (!id) throw new Error(\"missing\");\n"
            "  client.api.send(id);\n"
            "  state.count += 1;\n"
            "}\n"
            "export class Child extends Base {}\n",
            "id",
            "unannotated",
            "extends Base",
            "!id",
            'new Error("missing")',
        ),
        (
            "Api.kt",
            "suspend fun load(id: String): Result {\n"
            "  if (id == null) throw IllegalArgumentException(\"missing\")\n"
            "  client.api.send(id)\n"
            "  state.count += 1\n"
            "}\n"
            "class Child : Base(), Runner\n",
            "id: String",
            "Result",
            "Base(), Runner",
            "id == null",
            'IllegalArgumentException("missing")',
        ),
    ],
)
def test_non_python_structural_fact_kinds(
    tmp_path: Path,
    path: str,
    source: str,
    parameters: str,
    returns: str,
    bases: str,
    branch: str,
    error: str,
) -> None:
    (tmp_path / path).write_text(source, encoding="utf-8")
    valid = [
        _record(
            "function-signature",
            path,
            "1-1",
            "load",
            parameters=parameters,
            returns=returns,
            **{"async": "true"},
        ),
        _record("class-signature", path, "6-6", "Child", bases=bases),
        _record("call-edge", path, "1-5", "load", caller="load", callee="client.api.send"),
        _record("external-call", path, "3-3", "client.api.send", callee="client.api.send"),
        _record("branch", path, "2-2", branch, condition=branch),
        _record("error", path, "2-2", error, error=error),
        _record("side-effect", path, "4-4", "state.count", effect="state.count += 1"),
    ]
    assert all(_check(tmp_path, fact) == [] for fact in valid)

    invalid = [
        _record(
            "function-signature",
            path,
            "1-1",
            "load",
            parameters=parameters,
            returns="Wrong",
            **{"async": "true"},
        ),
        _record("class-signature", path, "6-6", "Child", bases="Wrong"),
        _record("call-edge", path, "1-5", "load", caller="load", callee="client.missing"),
        _record("external-call", path, "3-3", "client.api.send", callee="client.missing"),
        _record("branch", path, "2-2", branch, condition="different"),
        _record("error", path, "2-2", error, error="DifferentError()"),
        _record("side-effect", path, "4-4", "state.count", effect="state.count = 0"),
        _record("side-effect", path, "2-2", branch, effect=branch),
    ]
    assert all(_check(tmp_path, fact) for fact in invalid)


@pytest.mark.parametrize(
    (
        "path",
        "source",
        "function_line",
        "class_line",
        "call_line",
        "branch_line",
        "effect_line",
        "name",
        "parameters",
        "returns",
        "bases",
        "callee",
        "branch",
        "error",
        "effect",
        "is_async",
    ),
    [
        (
            "api.go",
            "package api\n\n"
            "type Child struct {\n    Base\n    Runner\n}\n\n"
            "func Load(id string) (Result, error) {\n"
            '    if id == "" { panic("missing") }\n'
            "    client.Api.Send(id)\n"
            "    state.Count += 1\n"
            "    return Result{}, nil\n"
            "}\n",
            8,
            3,
            10,
            9,
            11,
            "Load",
            "id string",
            "(Result, error)",
            "Base, Runner",
            "client.Api.Send",
            'id == ""',
            'panic("missing")',
            "state.Count += 1",
            "false",
        ),
        (
            "Api.java",
            "class Child extends Base implements Runner {\n"
            "    Result load(String id) {\n"
            '        if (id == null) throw new IllegalArgumentException("missing");\n'
            "        client.api.send(id);\n"
            "        state.count += 1;\n"
            "        return null;\n"
            "    }\n"
            "}\n",
            2,
            1,
            4,
            3,
            5,
            "load",
            "String id",
            "Result",
            "extends Base implements Runner",
            "client.api.send",
            "(id == null)",
            'new IllegalArgumentException("missing")',
            "state.count += 1",
            "false",
        ),
        (
            "api.rs",
            "struct Child;\n"
            "trait Base {}\n"
            "impl Base for Child {}\n\n"
            "async fn load(id: &str) -> Result<Value, Error> {\n"
            '    if id.is_empty() { panic!("missing"); }\n'
            "    client.api.send(id);\n"
            "    state.count += 1;\n"
            "    Ok(Value {})\n"
            "}\n",
            5,
            1,
            7,
            6,
            8,
            "load",
            "id: &str",
            "Result<Value, Error>",
            "Base",
            "client.api.send",
            "id.is_empty()",
            'panic!("missing")',
            "state.count += 1",
            "true",
        ),
        (
            "api.rb",
            "class Child < Base\n"
            "  def load(id)\n"
            '    raise ArgumentError, "missing" if id.nil?\n'
            "    client.api.send(id)\n"
            "    @count += 1\n"
            "  end\n"
            "end\n",
            2,
            1,
            4,
            3,
            5,
            "load",
            "id",
            "unannotated",
            "< Base",
            "client.api.send",
            "id.nil?",
            'raise ArgumentError, "missing"',
            "@count += 1",
            "false",
        ),
    ],
)
def test_go_java_rust_and_ruby_structural_fact_kinds(
    tmp_path: Path,
    path: str,
    source: str,
    function_line: int,
    class_line: int,
    call_line: int,
    branch_line: int,
    effect_line: int,
    name: str,
    parameters: str,
    returns: str,
    bases: str,
    callee: str,
    branch: str,
    error: str,
    effect: str,
    is_async: str,
) -> None:
    (tmp_path / path).write_text(source, encoding="utf-8")
    end_line = len(source.splitlines())
    valid = [
        _record(
            "function-signature",
            path,
            f"{function_line}-{function_line}",
            name,
            parameters=parameters,
            returns=returns,
            **{"async": is_async},
        ),
        _record("class-signature", path, f"{class_line}-{class_line}", "Child", bases=bases),
        _record("call-edge", path, f"{function_line}-{end_line}", name, caller=name, callee=callee),
        _record("external-call", path, f"{call_line}-{call_line}", callee, callee=callee),
        _record("branch", path, f"{branch_line}-{branch_line}", branch, condition=branch),
        _record("error", path, f"{branch_line}-{branch_line}", error, error=error),
        _record("side-effect", path, f"{effect_line}-{effect_line}", effect, effect=effect),
    ]
    assert all(_check(tmp_path, fact) == [] for fact in valid)

    invalid = [
        _record(
            "function-signature",
            path,
            f"{function_line}-{function_line}",
            name,
            parameters=parameters,
            returns="Wrong",
            **{"async": is_async},
        ),
        _record("class-signature", path, f"{class_line}-{class_line}", "Child", bases="Wrong"),
        _record("call-edge", path, f"{function_line}-{end_line}", name, caller=name, callee="missing.call"),
        _record("external-call", path, f"{call_line}-{call_line}", callee, callee="missing.call"),
        _record("branch", path, f"{branch_line}-{branch_line}", branch, condition="different"),
        _record("error", path, f"{branch_line}-{branch_line}", error, error="DifferentError"),
        _record("side-effect", path, f"{effect_line}-{effect_line}", effect, effect="different = 1"),
    ]
    assert all(_check(tmp_path, fact) for fact in invalid)


def test_unsupported_language_keeps_grounding_without_language_failure(tmp_path: Path) -> None:
    (tmp_path / "Api.swift").write_text("func load() {}\n", encoding="utf-8")
    fact = _record(
        "function-signature",
        "Api.swift",
        "1-1",
        "load",
        parameters="none",
        returns="void",
        **{"async": "false"},
    )
    assert _check(tmp_path, fact) == []


def test_missing_recognized_grammar_reports_parser_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "api.go").write_text("package api\nfunc Load() {}\n", encoding="utf-8")
    real_import = plan_runtime.importlib.import_module

    def missing_go(name: str):
        if name == "tree_sitter_go":
            raise ModuleNotFoundError("No module named 'tree_sitter_go'", name="tree_sitter_go")
        return real_import(name)

    monkeypatch.setattr(plan_runtime.importlib, "import_module", missing_go)
    fact = _record(
        "function-signature",
        "api.go",
        "2-2",
        "Load",
        parameters="",
        returns="unannotated",
        **{"async": "false"},
    )
    assert _check(tmp_path, fact) == ["fact.parser_dependency"]


def test_supported_language_syntax_error_blocks_structural_fact(tmp_path: Path) -> None:
    (tmp_path / "broken.ts").write_text(
        "export function load(raw: string {\n", encoding="utf-8"
    )
    fact = _record(
        "function-signature",
        "broken.ts",
        "1-1",
        "load",
        parameters="raw: string",
        returns="unannotated",
        **{"async": "false"},
    )
    assert _check(tmp_path, fact) == ["fact.structured"]
