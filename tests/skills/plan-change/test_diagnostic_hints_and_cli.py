from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import DIAGNOSTIC_HINTS, Diagnostic  # noqa: E402


def _literal_diagnostic_codes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Diagnostic"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


def test_every_literal_diagnostic_code_has_a_plain_language_hint() -> None:
    emitted = _literal_diagnostic_codes(ROOT / "tools" / "plan_contract_runtime.py")
    emitted |= _literal_diagnostic_codes(SCRIPTS / "check_plan.py")
    assert emitted <= set(DIAGNOSTIC_HINTS)
    assert all(value.endswith(".") for value in DIAGNOSTIC_HINTS.values())


def test_diagnostic_text_and_json_include_the_hint() -> None:
    diagnostic = Diagnostic("fact.stale", "fingerprints changed", 12)
    assert "Likely fix:" in str(diagnostic)
    payload = diagnostic.to_dict()
    assert payload["code"] == "fact.stale"
    assert payload["message"] == "fingerprints changed"
    assert payload["line"] == 12
    assert payload["hint"] == DIAGNOSTIC_HINTS["fact.stale"]
    assert payload["category"] == "stale_evidence"
    assert payload["skill"] == "plan-change"
    assert payload["valid_repairs"] == [DIAGNOSTIC_HINTS["fact.stale"]]
    assert payload["supporting_evidence"] == ["fingerprints changed"]


@pytest.mark.parametrize(
    ("script", "missing"),
    [
        ("prepare_plan.py", "plan_contract"),
        ("check_plan.py", "plan_inventory"),
        ("finalize_plan.py", "check_plan"),
    ],
)
def test_cli_import_failure_is_one_line_and_names_the_missing_import(
    tmp_path: Path, script: str, missing: str
) -> None:
    isolated = tmp_path / "isolated" / "scripts"
    isolated.mkdir(parents=True)
    shutil.copy2(SCRIPTS / script, isolated / script)
    result = subprocess.run(
        [sys.executable, str(isolated / script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.strip().splitlines() == [
        f"{script}: missing required import '{missing}' under skill root '{isolated.parent}'."
    ]
