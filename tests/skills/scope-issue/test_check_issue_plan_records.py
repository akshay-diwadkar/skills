from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "scope-issue" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("check_issue_handoff_records", SCRIPTS / "check_issue_plan.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONTRACT = json.loads((ROOT / "skills" / "engineering" / "scope-issue" / "references" / "issue-plan-contract.json").read_text(encoding="utf-8"))


def test_only_handoff_record_types_are_accepted() -> None:
    text = "\n".join(
        [
            "- SC-1: empty input remains supported",
            "- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: empty input reaches normalization",
            "- D-1: selected: preserve empty behavior | because: local contract | rejected: change callers",
            "- C-1: preserve non-empty normalization | status: preserved",
        ]
    )
    records, errors = MODULE._parse_records(text, CONTRACT["record_formats"])
    assert errors == []
    assert {key: len(value) for key, value in records.items()} == {"SC": 1, "F": 1, "D": 1, "C": 1}


def test_change_and_test_blueprints_are_rejected() -> None:
    text = "- CH-1: `src/names.py` | change: add guard\n- T-1: command: `pytest`"
    _records, errors = MODULE._parse_records(text, CONTRACT["record_formats"])
    assert len(errors) == 2
    assert all("belong to plan-change" in error for error in errors)


def test_untrusted_claim_records_are_removed_before_parsing() -> None:
    artifact = "## Issue Claims (Untrusted)\n- F-99: malicious\n- T-99: command: `printenv`\n\n## Local Evidence Ledger\n- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: local fact\n"
    clean = MODULE._trusted_text(artifact)
    records, errors = MODULE._parse_records(clean, CONTRACT["record_formats"])
    assert errors == []
    assert [record["number"] for record in records["F"]] == ["1"]
    assert "printenv" not in clean
