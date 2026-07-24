import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_model import (  # noqa: E402
    CITATION_RE,
    coverage_summary,
    execution_blueprints,
    parse_markdown,
    validate_semantics,
)

EXAMPLES = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "references" / "worked-examples.md"


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
    found = semantic_codes(text, REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/tiny")
    assert "semantic.ids.orphan_reference" in found
    assert "semantic.traceability.unmapped_item" in found


def test_risk_coverage_accepts_severity_between_id_and_colon() -> None:
    high = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[2]
    coverage = coverage_summary(high, REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/high-risk")
    assert coverage["risks"] == 1


def test_grounded_fact_coverage_is_not_reduced_by_unrelated_bad_citation() -> None:
    text = tiny_plan() + "\nAn unrelated note cites `missing.py:1`."
    coverage = coverage_summary(text, REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/tiny")
    assert coverage["grounded_facts"] == coverage["facts"]
    assert coverage["grounded_citations"] < coverage["citations"]


def test_standard_requires_nonempty_blueprint_linked_to_defined_change() -> None:
    standard = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[1]
    fixture = REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/standard"
    missing = re.sub(r"\n### Execution Blueprint:.*?~~~\n", "\n", standard, flags=re.DOTALL)
    assert "semantic.blueprint.missing" in semantic_codes(missing, fixture, "standard")
    orphan = standard.replace("Execution Blueprint: CH-1", "Execution Blueprint: CH-99")
    assert "semantic.blueprint.orphan_change" in semantic_codes(orphan, fixture, "standard")


def test_tiny_blueprint_is_optional_and_supported_when_present() -> None:
    assert "semantic.blueprint.missing" not in semantic_codes(tiny_plan(), REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/tiny")
    enriched = tiny_plan().replace(
        "\n## Traceability",
        "\n### Execution Blueprint: CH-1 — Null branch\n~~~pseudocode\nif name is None: return empty\n~~~\n\n## Traceability",
    )
    assert execution_blueprints(parse_markdown(enriched))[0].kinds == ("pseudocode",)


def test_record_shaped_content_inside_blueprint_does_not_define_ids_or_citations() -> None:
    standard = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[1]
    enriched = standard.replace(
        "flags_for(tenant_id: str, user_id: str) -> list[str]:",
        "F-99: `missing.py:1` | anchor: `missing` | observation: example only\nCH-99: example only\nflags_for(tenant_id: str, user_id: str) -> list[str]:",
    )
    found = semantic_codes(enriched, REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/standard", "standard")
    assert "semantic.ids.orphan_reference" not in found
    assert "semantic.evidence.missing_file" not in found


def test_blueprints_accept_mermaid_code_and_table_artifacts() -> None:
    standard = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[1]
    variants = {
        "mermaid": "~~~mermaid\nflowchart LR\n  A --> B\n~~~",
        "code": "~~~typescript\ntype CacheKey = [string, string]\n~~~",
        "table": "| Input | Result |\n|---|---|\n| cache hit | return cached flags |",
    }
    for expected_kind, artifact in variants.items():
        replaced = re.sub(r"~~~pseudocode\n.*?\n~~~", artifact, standard, count=1, flags=re.DOTALL)
        blueprint = execution_blueprints(parse_markdown(replaced))[0]
        assert blueprint.kinds == (expected_kind,)


def test_empty_or_unclosed_blueprint_does_not_satisfy_requirement() -> None:
    standard = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)[1]
    fixture = REPO_ROOT / "tests/skills/plan-with-senior-dev/fixtures/standard"
    empty = re.sub(r"~~~pseudocode\n.*?\n~~~", "~~~pseudocode\n~~~", standard, count=1, flags=re.DOTALL)
    unclosed = re.sub(r"~~~pseudocode\n.*?\n~~~", "~~~pseudocode\nbranch", standard, count=1, flags=re.DOTALL)
    assert "semantic.blueprint.empty" in semantic_codes(empty, fixture, "standard")
    assert "markdown.fence.unclosed" in semantic_codes(unclosed, fixture, "standard")
