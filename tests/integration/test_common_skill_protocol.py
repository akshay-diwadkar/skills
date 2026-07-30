from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tools" / "skill_cli.py"
SKILL = ROOT / "skills" / "engineering" / "plan-change"
TARGET = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / "tiny"
SCHEMA = json.loads((ROOT / "tools" / "skill_protocol" / "response.schema.json").read_text())


def snapshot() -> dict[str, str]:
    return {
        path.relative_to(SKILL).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(SKILL.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def run(*args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--skill-dir",
            str(SKILL),
            "--repo-root",
            str(TARGET),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    jsonschema.validate(payload, SCHEMA)
    return result, payload


def tiny_example() -> str:
    text = (SKILL / "references" / "worked-examples.md").read_text(encoding="utf-8")
    match = re.search(r"<!-- tiny-plan:start -->\n```markdown\n(.*?)\n```\n<!-- tiny-plan:end -->", text, re.DOTALL)
    assert match is not None
    return match.group(1) + "\n"


def test_plan_change_common_protocol_lifecycle_preserves_installed_skill(tmp_path: Path) -> None:
    before = snapshot()
    request = tmp_path / "request.md"
    request.write_text(
        "Fix normalize_name so None returns an empty string while preserving non-null normalization.\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    common = ["--run-dir", str(run_dir), "--format", "json"]

    doctor_result, doctor = run("--format", "json", "doctor")
    assert doctor_result.returncode == 0
    assert doctor["status"] == "ready"

    start_result, started = run(
        *common,
        "--input",
        f"request_file={request}",
        "--input",
        "tier=tiny",
        "--input",
        "intent=bug-fix",
        "--input",
        "anchor=src/names.py:normalize_name",
        "start",
    )
    assert start_result.returncode == 0
    assert started["phase"] == "drafting"

    status_result, status = run(*common, "status")
    assert status_result.returncode == 0
    assert status["phase"] == "drafting"

    blocked_result, blocked = run(*common, "next")
    assert blocked_result.returncode == 3
    assert blocked["status"] == "blocked"
    assert blocked["phase"] == "drafting"

    (run_dir / "draft.md").write_text(tiny_example(), encoding="utf-8")
    validate_result, validated = run(*common, "next")
    assert validate_result.returncode == 0
    assert validated["phase"] == "validated"

    finalize_result, complete = run(*common, "next")
    assert finalize_result.returncode == 0
    assert complete["phase"] == "complete"
    assert complete["status"] == "complete"
    assert (run_dir / "final.md").is_file()

    final_status_result, final_status = run(*common, "status")
    assert final_status_result.returncode == 0
    assert final_status["phase"] == "complete"
    assert snapshot() == before
