import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "plan-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_model import CITATION_RE, coverage_summary, parse_markdown, validate_semantics  # noqa: E402


EXAMPLES = REPO_ROOT / "plan-with-senior-dev" / "references" / "worked-examples.md"


def tiny_plan() -> str:
    return re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[0]


def semantic_codes(text: str, repo_root: Path, tier: str = "tiny") -> set[str]:
    return {item.code for item in validate_semantics(text, tier, repo_root)}


def test_parser_supports_tilde_fences_and_reports_unclosed_fence() -> None:
    document = parse_markdown("# Fix parser behavior now\n~~~python\nvalue = 1\n~~~\n")
    assert document.code_blocks[0].body == "value = 1"
    assert parse_markdown("# Fix parser behavior now\n```python\nvalue = 1\n").diagnostics


def test_citation_parser_preserves_multi_dot_dotfile_and_windows_paths() -> None:
    samples = {
        "`test/service.test.ts:9`": "test/service.test.ts",
        "`.env.example:2`": ".env.example",
        "`C:\\repo with spaces\\src\\service.test.ts:12`": "C:\\repo with spaces\\src\\service.test.ts",
    }
    for sample, expected in samples.items():
        match = CITATION_RE.search(sample)
        assert match is not None
        assert match.group("path") == expected


def test_dotted_and_dotfile_citations_validate_against_real_files(tmp_path: Path) -> None:
    (tmp_path / "service.test.ts").write_text("const marker = true;\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("TOKEN=example\n", encoding="utf-8")
    text = (
        "- F-1: `service.test.ts:1` | anchor: `marker` | observation: test marker exists.\n"
        "- F-2: `.env.example:1` | anchor: `TOKEN` | observation: token key exists.\n"
    )
    found = semantic_codes(text, tmp_path)
    assert "semantic.evidence.missing_file" not in found
    assert "semantic.evidence.anchor_mismatch" not in found


def test_fact_anchor_must_exist_on_exact_cited_line(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("first = 1\nsecond = 2\n", encoding="utf-8")
    text = "- F-1: `real.py:1` | anchor: `second` | observation: fabricated relation.\n"
    assert "semantic.evidence.anchor_mismatch" in semantic_codes(text, tmp_path)


def test_existing_change_anchor_must_exist_but_new_anchor_may_not(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("def current():\n    return 1\n", encoding="utf-8")
    existing = "- CH-1: `real.py` | anchor: `imaginary` | status: existing | change: update it.\n"
    new = "- CH-1: `future.py` | anchor: `future_symbol` | status: new | change: add it.\n"
    assert "semantic.change.missing_anchor" in semantic_codes(existing, tmp_path)
    assert "semantic.change.missing_anchor" not in semantic_codes(new, tmp_path)


def test_orphan_ids_and_unmapped_changes_are_rejected() -> None:
    text = tiny_plan().replace("| SC-1 | CH-1, CH-2 | T-1 |", "| SC-1 | CH-99 | T-1 |")
    found = semantic_codes(text, REPO_ROOT / "tests/plan-with-senior-dev/fixtures/tiny")
    assert "semantic.ids.orphan_reference" in found
    assert "semantic.traceability.unmapped_item" in found


def test_risk_coverage_accepts_severity_between_id_and_colon() -> None:
    high = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[2]
    coverage = coverage_summary(high, REPO_ROOT / "tests/plan-with-senior-dev/fixtures/high-risk")
    assert coverage["risks"] == 1


def test_grounded_fact_coverage_is_not_reduced_by_unrelated_bad_citation() -> None:
    text = tiny_plan() + "\nAn unrelated note cites `missing.py:1`."
    coverage = coverage_summary(text, REPO_ROOT / "tests/plan-with-senior-dev/fixtures/tiny")
    assert coverage["grounded_facts"] == coverage["facts"]
    assert coverage["grounded_citations"] < coverage["citations"]
