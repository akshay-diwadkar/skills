from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_json_contract_is_complete_and_generated_data_is_current() -> None:
    contract = json.loads(
        (ROOT / "skills" / "engineering" / "plan-change" / "references" / "plan-contract.json").read_text()
    )
    assert set(contract["record_schemas"]) == {"SC", "F", "D", "CH", "P", "B", "O", "C", "R", "T", "A", "X"}
    assert set(contract["obligations"]) == set(contract["risk_domains"])
    assert set(contract["blueprint_concepts"]) == set(contract["risk_domains"])
    result = subprocess.run(
        [sys.executable, "tools/validation/generate_plan_contract.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
