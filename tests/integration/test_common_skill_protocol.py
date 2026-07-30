from __future__ import annotations

import hashlib
import json
import re
import shutil
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


def run(*args: str, repo: Path = TARGET) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(repo),
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

    doctor_result, doctor = run(
        *common,
        "--input",
        f"request_file={request}",
        "--input",
        "tier=tiny",
        "--input",
        "intent=bug-fix",
        "--input",
        "anchor=src/names.py:normalize_name",
        "doctor",
    )
    assert doctor_result.returncode == 0
    assert doctor["status"] == "ready"
    assert doctor["next_command"]["argv"][1] == str(CLI)

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
    assert started["next_command"]["argv"][1] == str(CLI)

    status_result, status = run(*common, "status")
    assert status_result.returncode == 0
    assert status["phase"] == "drafting"

    blocked_result, blocked = run(*common, "next")
    assert blocked_result.returncode == 3
    assert blocked["status"] == "blocked"
    assert blocked["phase"] == "drafting"

    premature_result, premature = run(*common, "finalize")
    assert premature_result.returncode == 3
    assert premature["blocking_reasons"] == ["phase.command_forbidden"]

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


def test_plan_change_common_protocol_blocks_stale_evidence(tmp_path: Path) -> None:
    target = tmp_path / "target"
    shutil.copytree(TARGET, target)
    request = tmp_path / "request.md"
    request.write_text(
        "Fix normalize_name so None returns an empty string while preserving non-null normalization.\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    common = ["--run-dir", str(run_dir), "--format", "json"]
    started, _ = run(
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
        repo=target,
    )
    assert started.returncode == 0
    (run_dir / "draft.md").write_text(tiny_example(), encoding="utf-8")
    source = target / "src" / "names.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# concurrent change\n", encoding="utf-8")
    result, response = run(*common, "next", repo=target)
    assert result.returncode == 3
    assert response["phase"] == "drafting"
    assert {"fact.stale", "binding.baseline_stale"} & set(response["blocking_reasons"])


def test_plan_change_common_protocol_rejects_run_state_inside_target(tmp_path: Path) -> None:
    request = tmp_path / "request.md"
    request.write_text("Plan a local fix.\n", encoding="utf-8")
    result, response = run(
        "--run-dir",
        str(TARGET / ".unsafe-run"),
        "--input",
        f"request_file={request}",
        "--input",
        "tier=tiny",
        "--input",
        "intent=bug-fix",
        "--format",
        "json",
        "start",
    )
    assert result.returncode == 2
    assert response["blocking_reasons"] == ["path.run_dir_in_repo"]
    assert not (TARGET / ".unsafe-run").exists()
