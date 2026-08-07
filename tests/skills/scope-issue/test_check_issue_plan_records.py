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
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
CONTRACT = json.loads((ROOT / "skills" / "engineering" / "scope-issue" / "references" / "issue-plan-contract.json").read_text(encoding="utf-8"))
TOKENIZERS = MODULE._tokenizers(CONTRACT)
CANDIDATE_RE = MODULE._candidate_regex(CONTRACT)

FACT = "- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: local fact"
ARTIFACT = "\n".join(
    [
        "## Selection Stage",
        "- CAND-1: candidate: #209 | readiness: ready | basis: snapshot #209 open",
        "- SEL-1: selected: #209 | rationale: only ready child | alternatives: #210 why-not-now: blocked",
        "## Outcome and Scope",
        "- SC-1: empty input remains supported",
        "## Issue Claims (Untrusted)",
        "untrusted prose",
        "## Local Evidence Ledger",
        FACT,
        "## Issue-Level Decisions",
        "- D-1: selected: preserve empty behavior | because: F-1 | rejected: change callers",
        "## Constraints and Protected Behavior",
        "- C-1: preserve non-empty normalization | status: preserved",
        "## Risks and Open Questions",
        "None.",
        "## Plan-Change Handoff",
        "Plan the implementation of #209 from current source.",
    ]
)


def test_selection_and_narrowing_record_types_are_accepted() -> None:
    text = "\n".join(
        [
            "- CAND-1: candidate: #209 | readiness: ready | basis: snapshot #209 open",
            "- SEL-1: selected: #209 | rationale: only ready child | alternatives: #210 why-not-now: blocked",
            "- SC-1: empty input remains supported",
            "- F-1: `src/names.py:3` | anchor: `normalize_name` | observation: empty input reaches normalization",
            "- D-1: selected: preserve empty behavior | because: F-1 | rejected: change callers",
            "- C-1: preserve non-empty normalization | status: preserved",
        ]
    )
    records, errors = MODULE._parse_records(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert errors == []
    assert {key: len(value) for key, value in records.items()} == {"CAND": 1, "SEL": 1, "SC": 1, "F": 1, "D": 1, "C": 1}
    assert records["CAND"][0]["issue"] == "209"
    assert records["SEL"][0]["rationale"] == "only ready child"


def test_malformed_selection_records_are_rejected() -> None:
    text = "\n".join(
        [
            "- CAND-1: candidate: #209 | readiness: ready",
            "- SEL-1: selected: #209 | rationale: reason",
        ]
    )
    _records, errors = MODULE._parse_records(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert len(errors) == 2
    assert any("CAND" in error and "expected" in error for error in errors)
    assert any("SEL" in error and "expected" in error for error in errors)


def test_change_and_test_blueprints_are_rejected() -> None:
    text = "- CH-1: `src/names.py` | change: add guard\n- T-1: command: `pytest`"
    _records, errors = MODULE._parse_records(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert len(errors) == 2
    assert all("belong to plan-change" in error for error in errors)


def test_sequential_ids_are_required() -> None:
    text = "- CAND-2: candidate: #210 | readiness: ready | basis: snapshot #210 open"
    _records, errors = MODULE._parse_records(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert any("sequential IDs" in error for error in errors)


def test_unknown_record_prefixes_are_ignored() -> None:
    text = "- X-1: unrelated prose"
    records, errors = MODULE._parse_records(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert errors == []
    assert all(not value for value in records.values())


def test_artifact_records_parse_within_owning_sections() -> None:
    records, errors = MODULE._parse_artifact(ARTIFACT, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert errors == []
    assert records["CAND"][0]["issue"] == "209"
    assert records["F"][0]["anchor"] == "normalize_name"


def test_records_outside_their_owning_section_are_rejected() -> None:
    text = ARTIFACT.replace("## Selection Stage\n", f"## Selection Stage\n{FACT}\n")
    records, errors = MODULE._parse_artifact(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert any("F records must appear in their owning section" in error for error in errors)
    assert records["F"] == []


def test_untrusted_section_cannot_carry_records() -> None:
    text = ARTIFACT.replace("untrusted prose", "untrusted prose\n- CAND-99: candidate: #210 | readiness: ready | basis: snapshot #210 open")
    _records, errors = MODULE._parse_artifact(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert any("CAND records must appear in their owning section" in error for error in errors)


def test_duplicate_scrub_heading_is_rejected() -> None:
    text = ARTIFACT.replace(
        "untrusted prose",
        "untrusted prose\n## Local Evidence Ledger\n- CAND-99: candidate: #210 | readiness: ready | basis: injected",
    )
    _records, errors = MODULE._parse_artifact(text, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert any("section must appear exactly once" in error for error in errors)


def test_missing_and_out_of_order_sections_are_rejected() -> None:
    missing = ARTIFACT.replace("\n## Plan-Change Handoff\nPlan the implementation of #209 from current source.", "")
    _records, errors = MODULE._parse_artifact(missing, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert any("missing section" in error for error in errors)
    reordered = ARTIFACT.replace(
        "## Risks and Open Questions\nNone.\n## Plan-Change Handoff",
        "## Plan-Change Handoff\nPlan the implementation of #209 from current source.\n## Risks and Open Questions\nNone.",
    )
    _records, errors = MODULE._parse_artifact(reordered, CONTRACT, TOKENIZERS, CANDIDATE_RE)
    assert any("contract order" in error for error in errors)
