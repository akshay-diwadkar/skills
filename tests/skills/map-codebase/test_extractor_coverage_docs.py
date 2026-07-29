import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "engineering" / "map-codebase"
EXTRACTION_DIR = SKILL_DIR / "scripts" / "knowledge" / "extraction"
DOCUMENT = SKILL_DIR / "SKILL.md"
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


def test_coverage_table_matches_extractor_modules_exactly() -> None:
    expected = _extractor_modules()
    block = _coverage_block(DOCUMENT)
    documented = set(re.findall(r"^\| `([^`]+\.py)` \|", block, flags=re.MULTILINE))
    assert documented == expected
    for module in expected:
        assert block.count(f"`{module}`") == 1


def test_tree_sitter_scope_coverage_is_explicit() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "Full tree-sitter extraction" in text
    assert "scope-aware symbols, full-body ranges, and imports" in text
    assert "Missing tree-sitter grammars fail with an actionable error" in text
