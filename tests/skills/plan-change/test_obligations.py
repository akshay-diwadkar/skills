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


def test_copied_generic_obligation_ownership_is_rejected(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"])
    text = re.sub(r"tests: T-\d+", "tests: T-2", text)
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "obligation.generic_ownership" for item in diagnostics)


def test_obligation_requires_relevant_test_ownership(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"])
    text = text.replace(
        "given: security boundary with exact principal precondition",
        "given: security boundary with exact generic precondition",
    ).replace(
        "then: exact principal outcome is verified",
        "then: exact generic outcome is verified",
    ).replace(
        "when: named principal path runs",
        "when: named generic path runs",
    )
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "obligation.test_ownership" for item in diagnostics)
