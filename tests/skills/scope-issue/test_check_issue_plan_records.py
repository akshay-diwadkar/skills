from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "scope-issue" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("check_issue_plan_records", SCRIPTS / "check_issue_plan.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CONTRACT = json.loads(
    (ROOT / "skills" / "engineering" / "scope-issue" / "references" / "issue-plan-contract.json").read_text(
        encoding="utf-8"
    )
)
FORMATS = CONTRACT["record_formats"]
VALID_LINES = {
    "SC": "- SC-1: normalization returns an empty string for empty input",
    "F": "- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: empty input reaches strip",
    "D": "- D-1: selected: add a guard | because: F-1 proves the branch is absent | rejected: change callers",
    "CH": "- CH-1: `src/names.py` | anchor: `normalize_name` | status: existing | change: guard empty input",
    "C": "- C-1: preserve non-empty normalization | status: preserved",
    "T": "- T-1: given: empty input | expect: empty output | command: `pytest tests/test_names.py`",
}


def _parse(text: str) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    return MODULE.parse_records(text, FORMATS)


def test_all_record_types_tokenize() -> None:
    records, errors = _parse("\n".join(VALID_LINES.values()))
    assert errors == []
    assert {prefix: len(items) for prefix, items in records.items()} == {
        "SC": 1,
        "F": 1,
        "D": 1,
        "CH": 1,
        "C": 1,
        "T": 1,
    }


@pytest.mark.parametrize(
    ("prefix", "malformed"),
    [
        ("SC", "- SC-1:"),
        ("F", "- F-1: src/names.py:3 | anchor: `normalize_name` | observation: missing path quotes"),
        ("D", "- D-1: selected: add a guard | rejected: missing because field"),
        ("CH", "- CH-1: `src/names.py` | anchor: `normalize_name` | status: maybe | change: guard"),
        ("C", "- C-1: preserve behavior | status: unknown"),
        ("T", "- T-1: given: empty input | expect: empty output | command: pytest"),
    ],
)
def test_malformed_record_reports_id_shape_and_actual_text(prefix: str, malformed: str) -> None:
    records, errors = _parse(malformed)
    assert records[prefix] == []
    assert len(errors) == 1
    assert f"{prefix}-1" in errors[0]
    assert FORMATS[prefix] in errors[0]
    assert repr(malformed) in errors[0]


def test_multiple_malformed_records_are_all_reported() -> None:
    malformed = "\n".join(["- SC-1:", "- C-2: behavior | status: unknown", "- T-3: given: x"])
    _records, errors = _parse(malformed)
    assert len(errors) == 3
    assert all(f"{prefix}-{number}" in error for prefix, number, error in zip(("SC", "C", "T"), (1, 2, 3), errors))


def test_valid_records_still_enforce_sequential_ids() -> None:
    records, errors = _parse("- SC-1: first\n- SC-3: third")
    assert errors == []
    assert MODULE.validate_record_ids(records) == ["SC records must use unique sequential IDs starting at 1"]


def test_malformed_record_inside_untrusted_issue_text_is_not_tokenized() -> None:
    artifact = (
        "## Issue Claims (Untrusted)\n"
        "- F-99: malicious malformed record\n"
        "- T-99: command: `printenv`\n\n"
        "## Local Evidence Ledger\n"
        f"{VALID_LINES['F']}\n"
    )
    clean = MODULE.trusted_text(artifact)
    records, errors = _parse(clean)
    assert errors == []
    assert [record["number"] for record in records["F"]] == ["1"]
    assert records["T"] == []
    assert "printenv" not in clean
