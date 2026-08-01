from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "engineering" / "plan-change"
CLI = SKILL / "scripts" / "cli.py"
TARGET = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / "tiny"
SCHEMA = json.loads((ROOT / "tools" / "skill_protocol" / "response.schema.json").read_text())


def snapshot() -> dict[str, str]:
    return {
        path.relative_to(SKILL).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(SKILL.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def draft(anchor: str = "normalize_name") -> str:
    return f"""# Fix absent-name normalization

<!-- plan-contract: 6 -->
<!-- plan-metadata: {{"intent":"bug-fix","tier":"tiny","risk_domains":[]}} -->

## Outcome
SC-1: given: an absent input name | when: normalize_name handles the value | then: it returns an empty string | unchanged: present names remain normalized

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: {anchor} | claim: normalize_name owns normalization

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: return an empty string before stripping and lowering present names | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: absent and present names | when: targeted normalization tests execute | then: absent input is empty and present input stays normalized | command: python -m pytest tests/test_names.py -q
"""


def run(*args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(TARGET), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    jsonschema.validate(payload, SCHEMA)
    return result, payload


def test_plan_change_common_protocol_is_stateless_and_preserves_skill(tmp_path: Path) -> None:
    before = snapshot()
    request = tmp_path / "request.md"
    plan = tmp_path / "plan.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    plan.write_text(draft(), encoding="utf-8")
    inputs = ["--input", f"request_file={request}", "--input", f"draft_file={plan}", "--format", "json"]

    doctor_result, doctor = run(*inputs, "doctor")
    assert doctor_result.returncode == 0
    assert doctor["status"] == "ready"
    assert doctor["next_command"]["argv"][-1] == "run"

    run_result, complete = run(*inputs, "run")
    assert run_result.returncode == 0
    assert complete["status"] == complete["phase"] == "complete"
    assert complete["result"].startswith("# Fix absent-name normalization")
    assert "<!-- plan-proof:" in complete["result"]
    assert "<!-- plan-validation: 6;" in complete["result"]
    assert not list(tmp_path.rglob(".skill-cli-state.json"))
    assert snapshot() == before


def test_plan_change_common_protocol_returns_structured_repair(tmp_path: Path) -> None:
    request = tmp_path / "request.md"
    plan = tmp_path / "plan.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    plan.write_text(draft("fabricated_anchor"), encoding="utf-8")
    result, response = run(
        "--input",
        f"request_file={request}",
        "--input",
        f"draft_file={plan}",
        "--format",
        "json",
        "run",
    )
    assert result.returncode == 3
    assert response["blocking_reasons"] == ["fact.anchor"]
    assert response["diagnostics"][0]["record"] == "F-1"
    assert response["diagnostics"][0]["required_action"] == "Correct F-1 lines or anchor."


def test_plan_change_stateless_run_rejects_run_dir(tmp_path: Path) -> None:
    request = tmp_path / "request.md"
    plan = tmp_path / "plan.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    plan.write_text(draft(), encoding="utf-8")
    result, response = run(
        "--run-dir",
        str(tmp_path / "run"),
        "--input",
        f"request_file={request}",
        "--input",
        f"draft_file={plan}",
        "--format",
        "json",
        "run",
    )
    assert result.returncode == 2
    assert response["blocking_reasons"] == ["path.run_dir_forbidden"]
