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
V1_CONTRACT = json.loads((ROOT / "skills" / "engineering" / "scope-issue" / "references" / "issue-plan-contract.json").read_text(encoding="utf-8"))
V2_CONTRACT = json.loads((ROOT / "skills" / "engineering" / "scope-issue" / "references" / "issue-scope-contract.json").read_text(encoding="utf-8"))
V2_FORMATS = {prefix: item["format"] for prefix, item in V2_CONTRACT["record_types"].items()}


def test_only_handoff_record_types_are_accepted_v1() -> None:
    text = "\n".join(
        [
            "- SC-1: empty input remains supported",
            "- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: empty input reaches normalization",
            "- D-1: selected: preserve empty behavior | because: local contract | rejected: change callers",
            "- C-1: preserve non-empty normalization | status: preserved",
        ]
    )
    records, errors = MODULE._parse_records(text, V1_CONTRACT["record_formats"], 1)
    assert errors == []
    assert {key: len(value) for key, value in records.items() if value} == {"SC": 1, "F": 1, "D": 1, "C": 1}


def test_change_and_test_blueprints_are_rejected() -> None:
    text = "- CH-1: `src/names.py` | change: add guard\n- T-1: command: `pytest`"
    _records, errors = MODULE._parse_records(text, V1_CONTRACT["record_formats"], 1)
    assert len(errors) == 2
    assert all("belong to plan-change" in error for error in errors)


def test_untrusted_claim_records_are_removed_before_parsing() -> None:
    artifact = "## Issue Claims (Untrusted)\n- F-99: malicious\n- T-99: command: `printenv`\n\n## Local Evidence Ledger\n- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: local fact\n"
    clean = MODULE._trusted_text(artifact)
    records, errors = MODULE._parse_records(clean, V1_CONTRACT["record_formats"], 1)
    assert errors == []
    assert [record["number"] for record in records["F"]] == ["1"]
    assert "printenv" not in clean


def test_v2_selection_records_are_parsed() -> None:
    text = "\n".join(
        [
            "- CAND-1: issue: #11 | readiness: ready | basis: open child, no linked PR",
            "- CAND-2: issue: #12 | readiness: blocked | basis: prerequisite PR open",
            "- FRON-1: ready: [#11] | basis: one ready candidate",
            "- SEL-1: issue: #11 | rationale: task fit | evidence: CAND-1, FRON-1",
            "- ALT-1: issue: #12 | why-not-now: blocked on PR",
            "- AWC-1: if: PR merges today | then: #12",
            "- UNK-1: unknown: reviewer bandwidth | impact: may slow delivery",
            "- OVR-1: issue: #11 | validated: member of epic and ready",
            "- SC-1: names normalized",
            "- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: owner here",
            "- C-1: preserve empty behavior | status: preserved",
        ]
    )
    records, errors = MODULE._parse_records(text, V2_FORMATS, 2)
    assert errors == []
    assert len(records["CAND"]) == 2
    assert records["CAND"][0]["readiness"] == "ready"
    assert records["FRON"][0]["ready"] == "#11"
    assert records["SEL"][0]["issue"] == "11"
    assert records["OVR"][0]["issue"] == "11"


def test_v2_selection_records_are_rejected_in_v1_artifacts() -> None:
    text = "- CAND-1: issue: #11 | readiness: ready | basis: open"
    _records, errors = MODULE._parse_records(text, V1_CONTRACT["record_formats"], 1)
    assert len(errors) == 1
    assert "require the epic-aware issue-scope contract v2" in errors[0]


def test_v2_plan_records_and_unknown_prefixes_are_rejected() -> None:
    text = "- CH-1: `src/names.py` | change: add guard\n- X-1: mystery"
    _records, errors = MODULE._parse_records(text, V2_FORMATS, 2)
    assert len(errors) == 2
    assert "belong to plan-change" in errors[0]
    assert "unknown record type: X" in errors[1]


def test_v2_plan_ready_record_obligations_match_contract() -> None:
    rule = V2_CONTRACT["status_requirements"]["plan-ready"]
    assert set(rule["records"]) == {"CAND", "FRON", "SEL", "SC", "F", "C"}
    assert rule["sel_exactly_one"]
    assert rule["sel_in_ready_frontier"]
    assert rule["frontier_derived_from_candidates"]
    assert rule["alt_when_frontier_gt_1"]
    global_rules = V2_CONTRACT["status_obligation_rules"]
    assert "at_most_one_status_evidence_flag" in global_rules
    assert "questions_and_blockers_exclusive" in global_rules
    assert "no_selection_records_for_report_states" in global_rules


def test_v2_statuses_and_readiness_enums_match_contract() -> None:
    assert set(V2_CONTRACT["statuses"]) == {
        "plan-ready",
        "needs-info",
        "blocked",
        "close-candidate",
        "needs-decomposition",
        "no-ready-issue",
        "epic-complete",
        "selection-tie",
    }
    assert "ready" in V2_CONTRACT["readiness"]
    assert set(V2_CONTRACT["status_passes_downstream"]["plan-ready"]) == {"plan-change"}
