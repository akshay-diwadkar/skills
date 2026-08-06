from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .v7_helpers import (  # type: ignore[import-not-found]
    RUNTIME,
    make_repo,
    tiny_plan,
)

validate_draft = RUNTIME.validate_draft

REQUEST = "Fix absent names so normalize_name returns an empty string for absent values.\n"
STANDARD_METADATA = '{"intent":"bug-fix","tier":"standard","risk_domains":[]}'


def codes(result: Any) -> set[str]:
    return {item.code for item in result.diagnostics}


def find(result: Any, code: str) -> list[Any]:
    return [item for item in result.diagnostics if item.code == code]


def _with_propagation(plan: str, record: str) -> str:
    return plan.replace("## Verification\n", f"## Propagation\n{record}\n\n## Verification\n", 1)


def test_uncovered_structured_request_item_is_named(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = (
        "# Requirements\n"
        "- Fix absent names so normalize_name returns an empty string for absent values.\n"
        "- Update the package re-export to expose normalize_name.\n"
    ).encode()
    result = validate_draft(tiny_plan(), repo, request_bytes=request)
    uncovered = find(result, "obligation.coverage")
    assert any(
        "Structured request item is uncovered: Update the package re-export to expose normalize_name" in d.message
        for d in uncovered
    )
    assert all(d.required_action for d in uncovered)


def test_coverage_missing_ch_or_t_names_the_rule(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("covered_by: SC-1, CH-1, T-1", "covered_by: SC-1")
    result = validate_draft(draft, repo)
    d = find(result, "obligation.coverage")
    assert d
    assert d[0].message == "Each obligation must cover at least one SC and one CH or T."
    assert d[0].record == "RQ-1"
    assert "RQ-1.covered_by" in d[0].required_action


def test_invalid_covered_by_reference_names_the_ref(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("covered_by: SC-1, CH-1, T-1", "covered_by: SC-1, CH-9, T-1")
    result = validate_draft(draft, repo)
    d = find(result, "reference.undefined")
    assert any("RQ-1.covered_by references invalid CH-9" in x.message for x in d)


def test_unknown_reference_names_record_and_ref(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("covers: SC-1, CH-1", "covers: SC-1, CH-9")
    result = validate_draft(draft, repo)
    d = find(result, "reference.undefined")
    assert any("Unknown reference CH-9" in x.message for x in d)
    assert any(x.record == "T-1" for x in d)


@pytest.mark.parametrize(
    ("depends_on", "defect"),
    [
        ("none, CH-2", "'none' cannot be mixed with CH references"),
        ("T-1", "'T-1' is not a valid CH reference"),
        ("CH-2, CH-2", "'CH-2' is duplicated"),
    ],
)
def test_dependency_invalid_names_the_exact_defect(depends_on: str, defect: str, tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("depends_on: none", f"depends_on: {depends_on}")
    result = validate_draft(draft, repo)
    d = find(result, "dependency.invalid")
    assert d
    assert d[0].message == f"depends_on must be 'none' or a unique comma-separated CH list; {defect}."
    assert d[0].record == "CH-1"
    assert "CH-1.depends_on" in d[0].required_action


def test_unknown_dependency_is_named(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("depends_on: none", "depends_on: CH-2")
    result = validate_draft(draft, repo)
    d = find(result, "dependency.missing")
    assert d and "Unknown dependency CH-2" in d[0].message


def test_weak_anchor_reports_material_repair(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    result = validate_draft(tiny_plan(request_anchor="names"), repo, request_bytes=REQUEST.encode())
    d = find(result, "obligation.anchor")
    assert d
    assert d[0].message == "Obligation anchor is weak or trivial."
    assert d[0].record == "RQ-1"
    assert "material request text" in d[0].required_action


def test_anchor_outside_request_is_named(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    result = validate_draft(tiny_plan(request_anchor="absent name fix"), repo, request_bytes=REQUEST.encode())
    d = find(result, "obligation.anchor")
    assert d
    assert "Obligation anchor is absent from the request or handoff." in d[0].message
    assert d[0].record == "RQ-1"


def test_tiny_propagation_without_evidence_offers_removal(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = _with_propagation(
        tiny_plan(),
        "P-1: surface: contract | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: checked locally",
    )
    result = validate_draft(draft, repo)
    d = find(result, "propagation.evidence")
    assert d
    assert d[0].record == "P-1"
    assert "Or remove P-1 when the change is local." in d[0].required_action


def test_standard_propagation_without_evidence_offers_only_citation(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = _with_propagation(
        tiny_plan(metadata=STANDARD_METADATA),
        "P-1: surface: contract | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: checked locally",
    )
    result = validate_draft(draft, repo)
    d = find(result, "propagation.evidence")
    assert d
    assert "Or remove P-1" not in d[0].required_action
    assert "Update P-1.reason to cite F-n and describe the bounded sweep." in d[0].required_action


def test_standard_local_change_requires_no_propagation_declaration(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    result = validate_draft(tiny_plan(metadata=STANDARD_METADATA), repo)
    d = find(result, "propagation.required")
    assert any("evidence-backed no-propagation declaration" in x.message for x in d)
    assert d[0].record == "CH-1"


def test_standard_local_change_fixed_by_declaration(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = _with_propagation(
        tiny_plan(metadata=STANDARD_METADATA),
        "P-1: surface: contract | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: F-1 bounded sweep found no external consumers",
    )
    assert validate_draft(draft, repo).valid


def test_shared_change_requires_propagation_record(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("locality: local", "locality: shared")
    result = validate_draft(draft, repo)
    d = find(result, "propagation.required")
    assert any(x.message == "Shared changes require at least one matching Propagation record." for x in d)
    assert any(x.record == "CH-1" for x in d)


def test_shared_change_fixed_by_distinct_surface(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = _with_propagation(
        tiny_plan().replace("locality: local", "locality: shared"),
        "P-1: surface: test | disposition: test-only | path: tests/test_names.py | owner: CH-1 | reason: tests exercise the shared normalization path",
    )
    assert validate_draft(draft, repo).valid


def test_field_grammar_defect_is_named(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    draft = tiny_plan().replace("reversibility: reversible", "reversibility: reversible | oops")
    result = validate_draft(draft, repo)
    d = find(result, "record.invalid")
    assert d
    assert any("no ': ' separator in 'oops'" in x.message for x in d)


def test_every_usability_diagnostic_carries_actionable_repair(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    mutations = [
        tiny_plan().replace("covered_by: SC-1, CH-1, T-1", "covered_by: SC-1"),
        tiny_plan().replace("depends_on: none", "depends_on: CH-2, CH-2"),
        tiny_plan().replace("locality: local", "locality: shared"),
        _with_propagation(
            tiny_plan(),
            "P-1: surface: contract | disposition: out-of-scope | path: src/names.py | owner: CH-1 | reason: checked locally",
        ),
    ]
    for draft in mutations:
        result = validate_draft(draft, repo)
        assert result.diagnostics
        for item in result.diagnostics:
            assert item.required_action
            assert "TODO" not in item.required_action
