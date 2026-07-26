import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "engineering" / "map-codebase"
EXTRACTION_DIR = SKILL_DIR / "scripts" / "knowledge" / "extraction"
DOCUMENTS = [SKILL_DIR / "SKILL.md", SKILL_DIR / "references" / "integration-guide.md"]
BEGIN = "<!-- BEGIN EXTRACTOR COVERAGE -->"
END = "<!-- END EXTRACTOR COVERAGE -->"


def _extractor_modules() -> set[str]:
    modules = set()
    for path in EXTRACTION_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("extract_") for node in ast.walk(tree)):
            modules.add(path.name)
    return modules


def _coverage_block(document: Path) -> str:
    text = document.read_text(encoding="utf-8")
    assert text.count(BEGIN) == 1
    assert text.count(END) == 1
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip()


def test_coverage_tables_match_extractor_modules_exactly() -> None:
    expected = _extractor_modules()
    blocks = [_coverage_block(document) for document in DOCUMENTS]
    assert blocks[0] == blocks[1]
    documented = set(re.findall(r"^\| `([^`]+\.py)` \|", blocks[0], flags=re.MULTILINE))
    assert documented == expected
    for module in expected:
        assert blocks[0].count(f"`{module}`") == 1


def test_lexical_only_limit_is_explicit_in_both_documents() -> None:
    for document in DOCUMENTS:
        text = document.read_text(encoding="utf-8")
        assert "Lexical-only means deterministic regex-based symbol and import discovery" in text
        assert "lower structural confidence" in text
