from __future__ import annotations

import importlib.util
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


def test_domain_attacks_are_required(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["external-integration"])
    text = "\n".join(line for line in text.splitlines() if not line.startswith("- A-ambiguous-success:")) + "\n"
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "attack.required" and "ambiguous-success" in item.message for item in diagnostics)


def test_attack_specific_dismissal_is_accepted(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text = text.replace(
        "observation: describe current branches errors calls and side effects",
        "observation: boundary input empty values are already rejected by the cited target",
    )
    line = next(line for line in text.splitlines() if line.startswith("- A-boundary-input:"))
    text = text.replace(
        line,
        "- A-boundary-input: status: dismissed | finding: boundary input empty value failure is already guarded | evidence: F-1 | resolution: F-1 | reason: boundary input empty values are already rejected",
    )
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert diagnostics == []


def test_copied_generic_dismissal_reasons_are_rejected(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text = text.replace(
        "observation: describe current branches errors calls and side effects",
        "observation: propagation consumer and boundary input checks already exist",
    )
    for attack in ("forgotten-propagation", "boundary-input"):
        line = next(line for line in text.splitlines() if line.startswith(f"- A-{attack}:"))
        text = text.replace(
            line,
            f"- A-{attack}: status: dismissed | finding: concrete {attack} failure is guarded | evidence: F-1 | resolution: F-1 | reason: propagation consumer and boundary input checks already exist",
        )
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "attack.generic_reason" for item in diagnostics)


def test_repaired_attack_requires_relevant_change_and_test(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text = text.replace("boundary input", "ordinary value")
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code in {"attack.specificity", "attack.ownership"} for item in diagnostics)


def test_unknown_attack_fails_closed(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text += "- A-invented: status: dismissed | finding: invented path is irrelevant | evidence: F-1 | resolution: F-1 | reason: invented path is absent\n"
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "attack.unknown" for item in diagnostics)
