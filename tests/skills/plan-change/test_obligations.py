from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import validate_plan  # noqa: E402

SPEC = importlib.util.spec_from_file_location("hardening_helpers", Path(__file__).with_name("hardening_helpers.py"))
assert SPEC and SPEC.loader
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def _principal_not_applicable(text: str) -> str:
    text = text.replace(
        "observation: describe current branches errors calls and side effects",
        "observation: no principal identity exists because tenant service credentials own requests",
    )
    line = next(line for line in text.splitlines() if "obligation: principal " in line)
    replacement = re.sub(
        r"status: satisfied \| coverage: (.*?) \| evidence: F-1 \| decision: D-1 \| changes: CH-1 \| tests: T-\d+",
        r"status: not-applicable | coverage: \1 | evidence: F-1 | reason: no principal identity exists because tenant service credentials own requests",
        line,
    )
    text = text.replace(line, replacement)
    text = text.replace("principal ->", "tenant ->")
    return text.replace("principal, tenant, trust boundary", "tenant, trust boundary")


def test_grounded_not_applicable_obligation_preserves_complete_matrix(tmp_path: Path) -> None:
    text = _principal_not_applicable(HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"]))
    plan, diagnostics = validate_plan(text, tmp_path)
    assert diagnostics == []
    assert plan is not None
    assert len(plan.records["O"]) == len(plan_contract_obligations("security"))


def plan_contract_obligations(domain: str) -> tuple[str, ...]:
    from plan_runtime import OBLIGATIONS

    return OBLIGATIONS[domain]


def test_not_applicable_requires_relevant_grounded_evidence(tmp_path: Path) -> None:
    text = _principal_not_applicable(HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"]))
    text = text.replace(
        "observation: no principal identity exists because tenant service credentials own requests",
        "observation: local target strips whitespace",
    )
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "obligation.not_applicable_evidence" for item in diagnostics)


def test_not_applicable_rejects_contradictory_change(tmp_path: Path) -> None:
    text = _principal_not_applicable(HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"]))
    text = text.replace("change: specify", "change: add principal validation and specify")
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "obligation.not_applicable_contradiction" for item in diagnostics)


def test_shared_related_test_covers_multiple_obligations(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"])
    plan, diagnostics = validate_plan(text, tmp_path)
    assert diagnostics == []
    assert plan is not None
    test_refs = [
        record.fields["tests"]
        for record in plan.records["O"]
        if record.fields["obligation"] in {"principal", "tenant", "trust-boundary", "authorization-owner"}
    ]
    assert len(set(test_refs)) == 1


def test_generic_multi_obligation_test_is_rejected(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"])
    text = re.sub(
        r"- T-2: .*",
        "- T-2: given: generic security setup | when: generic paths run | then: generic outcomes are verified | command: python -m pytest tests/test_security.py",
        text,
    )
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "obligation.test_ownership" for item in diagnostics)
