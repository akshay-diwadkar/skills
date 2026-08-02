import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from knowledge.discovery import discover_files, is_secret_file_or_content
from knowledge.extraction.base import infer_component_types, normalized_subsystem_path
from knowledge.extraction.python import extract_python_file
from knowledge.indexing import classify_and_extract


def test_discovery_inclusion_exclusion(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main(): pass\n", encoding="utf-8")
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "lib.py").write_text("def vendor(): pass\n", encoding="utf-8")

    config = {
        "include": ["src/**"],
        "exclude": ["**/vendor/**"],
        "generated": [],
        "max_file_size_bytes": 1048576,
    }

    inc, gen, ign = discover_files(tmp_path, config)
    assert "src/main.py" in inc
    assert "vendor/lib.py" not in inc


def test_secret_file_redaction(tmp_path: Path):
    secret_file = tmp_path / ".env"
    secret_file.write_text("AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")

    example_file = tmp_path / ".env.example"
    example_file.write_text("AWS_SECRET_ACCESS_KEY=example_value\n", encoding="utf-8")

    assert is_secret_file_or_content(secret_file, secret_file.read_text(encoding="utf-8"))
    assert not is_secret_file_or_content(example_file, example_file.read_text(encoding="utf-8"))


def test_python_ast_extraction(tmp_path: Path):
    py_file = tmp_path / "service.py"
    content = '''"""Auth service module."""

class AuthService(AuthContract):
    @route("/login")
    def login(self):
        try:
            return SETTINGS.authenticate()
        except AuthError:
            raise

@job
async def reset_password(user_id: str) -> bool:
    pass
'''
    py_file.write_text(content, encoding="utf-8")

    symbols, imports, conf, unks = extract_python_file(py_file, "service.py", content, "auth")
    assert conf == "high"
    assert len(unks) == 0

    sym_names = [s.name for s in symbols]
    assert "AuthService" in sym_names
    assert "reset_password" in sym_names
    login = next(symbol for symbol in symbols if symbol.name == "login")
    assert login.signature == "def login(self)"
    assert login.decorators == ["route('/login')"]
    assert login.references == ["SETTINGS"]
    assert login.calls == ["SETTINGS.authenticate", "route"]
    assert login.control_flow == ["raises", "try"]
    reset = next(symbol for symbol in symbols if symbol.name == "reset_password")
    assert reset.type_hints == ["bool", "str"]
    assert reset.component_types == ["service", "job"]
    service = next(symbol for symbol in symbols if symbol.name == "AuthService")
    assert service.interfaces == ["AuthContract"]
    assert service.component_types == ["service"]


def test_component_type_and_normalized_subsystem_inference(tmp_path: Path):
    source = tmp_path / "src" / "notifications" / "jobs" / "DigestService.py"
    source.parent.mkdir(parents=True)
    source.write_text("# Generated file; do not edit\nclass DigestService:\n    pass\n", encoding="utf-8")
    config = {
        "include": [],
        "exclude": [],
        "generated": ["src/**/DigestService.py"],
        "max_file_size_bytes": 1048576,
    }

    indexed, _, reason = classify_and_extract(tmp_path, str(source), config)

    assert reason is None
    assert indexed is not None
    assert indexed.record["normalized_subsystem_path"] == "notifications/jobs"
    assert indexed.record["component_types"] == ["service", "job", "generated"]
    assert indexed.symbols[0]["component_types"] == ["service", "job", "generated"]
    assert normalized_subsystem_path("lib/billing/repository/invoice.py") == "billing/repository"
    assert normalized_subsystem_path("packages/accounts/src/api/service.py") == "accounts/api"
    assert infer_component_types("docs/legacy-notes.md") == ["documentation", "legacy"]
    assert infer_component_types("exporter/compatibility/LegacyAdapter.cs") == ["legacy"]
