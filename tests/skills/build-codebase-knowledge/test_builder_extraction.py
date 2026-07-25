import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from knowledge.discovery import discover_files, is_secret_file_or_content
from knowledge.extraction.python import extract_python_file


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

class AuthService:
    def login(self):
        pass

async def reset_password(user_id: str):
    pass
'''
    py_file.write_text(content, encoding="utf-8")

    symbols, imports, conf, unks = extract_python_file(py_file, "service.py", content, "auth")
    assert conf == "high"
    assert len(unks) == 0

    sym_names = [s.name for s in symbols]
    assert "AuthService" in sym_names
    assert "reset_password" in sym_names
