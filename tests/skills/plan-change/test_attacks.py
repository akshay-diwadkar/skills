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


def test_domain_attacks_are_required_and_repaired_with_change_and_test(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["external-integration"])
    text = "\n".join(line for line in text.splitlines() if not line.startswith("- A-ambiguous-success:")) + "\n"
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "attack.required" and "ambiguous-success" in item.message for item in diagnostics)


def test_unknown_attack_fails_closed(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "tiny", [])
    text += "- A-invented: status: dismissed | finding: invented path is irrelevant | evidence: F-1 | resolution: F-1\n"
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "attack.unknown" for item in diagnostics)
