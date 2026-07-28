import importlib
import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from build_knowledge import build_knowledge
from knowledge.extraction.configuration import extract_config_and_commands
from knowledge.extraction.lexical import extract_lexical_file
from resolve_task import _literal_split, resolve_task


def test_protected_compounds_survive_camel_case_splitting() -> None:
    assert _literal_split("JavaScript TypeScript GitHub GitLab PostgreSQL OAuth GraphQL WebSocket") == {
        "javascript",
        "typescript",
        "github",
        "gitlab",
        "postgresql",
        "oauth",
        "graphql",
        "websocket",
    }
    assert "script" not in _literal_split("JavaScript")
    assert "type" not in _literal_split("TypeScript")


def test_javascript_extractor_beats_unrelated_script_match(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "src" / "javascript_extractor.py").write_text(
        "def extract_arrow_function_exports(source):\n"
        "    return [line for line in source.splitlines() if '=>' in line]\n",
        encoding="utf-8",
    )
    (tmp_path / "tools" / "script.py").write_text(
        "def export_script(value):\n    return value\n",
        encoding="utf-8",
    )
    knowledge = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, knowledge)

    result = resolve_task(
        tmp_path,
        "Fix the JavaScript extractor to handle arrow function exports",
        knowledge,
    )

    assert result["targets"][0]["path"] == "src/javascript_extractor.py"
    assert all(item != "symbol_token: script" for item in result["targets"][0]["evidence"])


def test_weak_evidence_families_cannot_reach_high_confidence(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "owner.py").write_text(
        "class LoginCoordinator:\n    def run(self):\n        return True\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_owner.py").write_text(
        "from src.owner import LoginCoordinator\n\ndef test_login():\n    assert LoginCoordinator().run()\n",
        encoding="utf-8",
    )
    knowledge = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, knowledge)

    result = resolve_task(tmp_path, "Harden login behavior", knowledge)

    assert result["targets"][0]["path"] == "src/owner.py"
    assert result["confidence"]["level"] == "medium"
    assert any("no exact symbol, exact path, or filename" in item for item in result["confidence"]["uncertainties"])


@pytest.mark.parametrize(
    ("filename", "content", "expected_name", "expected_import"),
    [
        (
            "service.go",
            'package service\nimport "example/project/store"\nfunc Handle() {\n println("ok")\n}\n',
            "Handle",
            "example/project/store",
        ),
        (
            "service.rs",
            "use crate::store::Record;\npub fn handle() {\n let _value = 1;\n}\n",
            "handle",
            "crate/store/Record",
        ),
        (
            "Service.java",
            "import example.project.Store;\nclass Service {\n void handle() {\n  return;\n }\n}\n",
            "handle",
            "example/project/Store",
        ),
        (
            "service.c",
            '#include "store.h"\nint handle(void) {\n return 1;\n}\n',
            "handle",
            "store.h",
        ),
        (
            "service.cpp",
            '#include "store.hpp"\nclass Service {\n public:\n  int handle() {\n   return 1;\n  }\n};\n',
            "handle",
            "store.hpp",
        ),
    ],
)
def test_tree_sitter_extracts_full_body_ranges_and_imports(
    tmp_path: Path,
    filename: str,
    content: str,
    expected_name: str,
    expected_import: str,
) -> None:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")

    symbols, imports, confidence, unknowns = extract_lexical_file(
        path,
        filename,
        content,
        "root",
    )

    symbol = next(item for item in symbols if item.name == expected_name)
    assert symbol.line_end > symbol.line_start
    assert expected_import in imports
    assert confidence == "high"
    assert unknowns == []


def test_missing_tree_sitter_grammar_fails_with_installation_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "service.go"
    original = importlib.import_module

    def missing(name: str):
        if name == "tree_sitter_go":
            raise ImportError(name)
        return original(name)

    monkeypatch.setattr("knowledge.extraction.lexical.importlib.import_module", missing)
    with pytest.raises(RuntimeError, match="requirements.txt"):
        extract_lexical_file(path, "service.go", "package service\n", "root")


def test_configuration_extractor_indexes_known_nested_keys(tmp_path: Path) -> None:
    pyproject = (
        "[tool.ruff]\nline-length = 100\n\n"
        "[tool.pytest.ini_options]\naddopts = '-q'\n"
    )
    package = '{"scripts":{"test":"node --test","lint":"eslint .","build":"tsc"}}'
    tsconfig = '{"compilerOptions":{"strict":true}}'

    pyproject_entry, _ = extract_config_and_commands(tmp_path, "pyproject.toml", pyproject)
    package_entry, _ = extract_config_and_commands(tmp_path, "package.json", package)
    tsconfig_entry, _ = extract_config_and_commands(tmp_path, "tsconfig.json", tsconfig)

    assert "tool.ruff.line-length" in pyproject_entry["keys"]
    assert "tool.pytest.ini_options.addopts" in pyproject_entry["keys"]
    assert {"scripts.test", "scripts.lint", "scripts.build"} <= set(package_entry["keys"])
    assert "compilerOptions.strict" in tsconfig_entry["keys"]
