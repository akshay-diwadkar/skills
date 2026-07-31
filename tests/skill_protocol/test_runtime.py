from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tools" / "skill_cli.py"
RESPONSE_SCHEMA = json.loads((ROOT / "tools" / "skill_protocol" / "response.schema.json").read_text())
MANIFEST_SCHEMA = json.loads((ROOT / "tools" / "skill_protocol" / "manifest.schema.json").read_text())


def manifest() -> dict[str, Any]:
    step = {
        "argv": ["{python}", "{skill_dir}/scripts/workflow.py", "{run_dir}"],
        "repeat": [{"input": "tag", "flag": "--tag"}],
        "capture_stdout": None,
        "diagnostics_json": False,
        "failure": "operational",
    }
    return {
        "protocol_version": "1.0",
        "skill": "fixture-skill",
        "minimum_python": "3.11",
        "run_dir_policy": "outside_skill",
        "requirements": [],
        "inputs": [
            {
                "name": "tag",
                "kind": "string",
                "required": False,
                "repeatable": True,
                "description": "Fixture tags.",
                "choices": [],
            }
        ],
        "artifacts": [{"name": "work", "path": "work.txt", "media_type": "text/plain"}],
        "phases": {
            "drafting": {
                "status": "in_progress",
                "next_action": "validate",
                "next_command": "validate",
                "required_reads": ["{run_dir}/work.txt"],
                "allowed_writes": ["{run_dir}/work.txt"],
                "forbidden_actions": ["write_installed_skill"],
            },
            "validated": {
                "status": "ready",
                "next_action": "finalize",
                "next_command": "finalize",
                "required_reads": ["{run_dir}/work.txt"],
                "allowed_writes": [],
                "forbidden_actions": ["write_installed_skill"],
            },
            "complete": {
                "status": "complete",
                "next_action": None,
                "next_command": None,
                "required_reads": ["{run_dir}/work.txt"],
                "allowed_writes": [],
                "forbidden_actions": ["write_installed_skill"],
            },
        },
        "commands": {
            "start": {"allowed_phases": ["drafting"], "success_phase": "drafting", "steps": [step]},
            "validate": {
                "allowed_phases": ["drafting", "validated"],
                "success_phase": "validated",
                "steps": [step],
            },
            "finalize": {
                "allowed_phases": ["validated"],
                "success_phase": "complete",
                "steps": [step],
            },
        },
    }


def create_skill(tmp_path: Path, payload: dict[str, Any] | None = None) -> Path:
    skill = tmp_path / "fixture-skill"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: fixture-skill\ndescription: Fixture.\nversion: 1.0.0\n---\n",
        encoding="utf-8",
    )
    (skill / "skill-protocol.json").write_text(json.dumps(payload or manifest()), encoding="utf-8")
    (scripts / "workflow.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "run = Path(sys.argv[1])\n"
        "run.mkdir(parents=True, exist_ok=False) if not run.exists() else None\n"
        "(run / 'work.txt').write_text(' '.join(sys.argv[2:]), encoding='utf-8')\n",
        encoding="utf-8",
    )
    return skill


def invoke(skill: Path, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--skill-dir",
            str(skill),
            "--repo-root",
            str(repo),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def json_result(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    payload = json.loads(result.stdout)
    jsonschema.validate(payload, RESPONSE_SCHEMA)
    return payload


def test_manifest_and_response_schemas_accept_reference_contract(tmp_path: Path) -> None:
    payload = manifest()
    jsonschema.validate(payload, MANIFEST_SCHEMA)
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    response = json_result(invoke(skill, repo, "--format", "json", "doctor"))
    assert response["status"] == "ready"


def test_generic_initial_phase_and_conditional_reads_are_supported(tmp_path: Path) -> None:
    payload = manifest()
    payload["inputs"][0].update({"required": True, "repeatable": False})
    payload["phases"]["implementing"] = payload["phases"].pop("drafting")
    payload["phases"]["implementing"]["conditional_reads"] = [
        {"input": "tag", "values": ["full"], "paths": ["{skill_dir}/SKILL.md"]}
    ]
    payload["commands"]["start"].update(
        {"allowed_phases": ["implementing"], "success_phase": "implementing"}
    )
    payload["commands"]["validate"]["allowed_phases"] = ["implementing", "validated"]
    jsonschema.validate(payload, MANIFEST_SCHEMA)
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    result = invoke(
        skill,
        repo,
        "--run-dir",
        str(run),
        "--input",
        "tag=full",
        "--format",
        "json",
        "start",
    )
    response = json_result(result)
    assert response["phase"] == "implementing"
    assert [Path(item["path"]).resolve() for item in response["required_reads"]] == [
        (run / "work.txt").resolve(),
        (skill / "SKILL.md").resolve(),
    ]


def test_doctor_returns_replayable_start_command_with_inputs(tmp_path: Path) -> None:
    payload = manifest()
    payload["inputs"][0].update({"required": True, "repeatable": True})
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    result = invoke(
        skill,
        repo,
        "--run-dir",
        str(run),
        "--input",
        "tag=one",
        "--input",
        "tag=two",
        "--format",
        "json",
        "doctor",
    )
    response = json_result(result)
    command = response["next_command"]
    assert command is not None
    replay = subprocess.run(command["argv"], cwd=command["cwd"], capture_output=True, text=True, check=False)
    assert replay.returncode == 0
    assert json_result(replay)["phase"] == "drafting"
    assert (run / "work.txt").read_text(encoding="utf-8") == "--tag one --tag two"


def test_lifecycle_repeated_inputs_state_and_idempotent_complete(tmp_path: Path) -> None:
    skill = create_skill(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    start = invoke(
        skill,
        repo,
        "--run-dir",
        str(run),
        "--input",
        "tag=one",
        "--input",
        "tag=two",
        "--format",
        "json",
        "start",
    )
    assert start.returncode == 0
    assert json_result(start)["phase"] == "drafting"
    assert (run / "work.txt").read_text(encoding="utf-8") == "--tag one --tag two"
    assert json_result(invoke(skill, repo, "--run-dir", str(run), "--format", "json", "status"))["phase"] == "drafting"
    assert json_result(invoke(skill, repo, "--run-dir", str(run), "--format", "json", "next"))["phase"] == "validated"
    assert json_result(invoke(skill, repo, "--run-dir", str(run), "--format", "json", "next"))["phase"] == "complete"
    complete = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "next")
    assert complete.returncode == 0
    assert json_result(complete)["phase"] == "complete"
    assert not list(run.glob("*.tmp"))


def test_classification_start_returns_result_and_next_binds_recommendation(tmp_path: Path) -> None:
    payload = manifest()
    payload["inputs"].extend(
        [
            {
                "name": "request_file",
                "kind": "path",
                "required": True,
                "repeatable": False,
                "description": "Trusted request.",
                "choices": [],
            },
            {
                "name": "classification_override",
                "kind": "path",
                "required": False,
                "repeatable": False,
                "description": "Override evidence.",
                "choices": [],
            },
        ]
    )
    payload["artifacts"].append(
        {"name": "classification", "path": "classification.json", "media_type": "application/json"}
    )
    payload["phases"]["classification_review"] = {
        "status": "ready",
        "next_action": "apply_deterministic_classification",
        "next_command": "apply_classification",
        "required_reads": ["{run_dir}/classification.json"],
        "result_artifact": "classification",
        "allowed_writes": [],
        "forbidden_actions": ["override_without_evidence"],
    }
    payload["classification"] = {
        "phase": "classification_review",
        "artifact": "classification",
        "required_inputs": ["request_file"],
        "controlled_inputs": ["tag"],
        "override_input": "classification_override",
        "argv": ["{python}", "{skill_dir}/scripts/classifier.py", "{input.request_file}"],
        "repeat": [],
    }
    skill = create_skill(tmp_path, payload)
    (skill / "scripts" / "classifier.py").write_text(
        "import json\n"
        "print(json.dumps({"
        "'recommendation': {'status': 'ready', 'values': {'tag': ['classified']}},"
        "'evidence': [], 'confidence': 'high', 'alternatives': [], 'override_requirements': []"
        "}))\n",
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    request = tmp_path / "request.md"
    request.write_text("fixture request", encoding="utf-8")
    run = tmp_path / "run"
    started = json_result(
        invoke(
            skill,
            repo,
            "--run-dir",
            str(run),
            "--input",
            f"request_file={request}",
            "--format",
            "json",
            "start",
        )
    )
    assert started["phase"] == "classification_review"
    assert started["result"]["recommendation"]["values"] == {"tag": ["classified"]}
    applied = json_result(invoke(skill, repo, "--run-dir", str(run), "--format", "json", "next"))
    assert applied["phase"] == "drafting"
    assert (run / "work.txt").read_text(encoding="utf-8") == "--tag classified"

    blocked_run = tmp_path / "blocked-run"
    json_result(
        invoke(
            skill,
            repo,
            "--run-dir",
            str(blocked_run),
            "--input",
            f"request_file={request}",
            "--format",
            "json",
            "start",
        )
    )
    rejected = invoke(
        skill,
        repo,
        "--run-dir",
        str(blocked_run),
        "--input",
        "tag=contrary",
        "--format",
        "json",
        "next",
    )
    assert rejected.returncode == 3
    assert json_result(rejected)["blocking_reasons"] == ["classification.override_required"]


def test_json_invocation_errors_are_machine_readable_and_stderr_free(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--format", "json", "start"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    payload = json_result(result)
    assert payload["blocking_reasons"] == ["invocation.invalid"]


def test_rejects_run_inside_skill_existing_run_and_state_identity_change(tmp_path: Path) -> None:
    skill = create_skill(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    unsafe = invoke(
        skill,
        repo,
        "--run-dir",
        str(skill / "run"),
        "--format",
        "json",
        "start",
    )
    assert unsafe.returncode == 2
    assert json_result(unsafe)["blocking_reasons"] == ["path.run_dir_in_skill"]

    run = tmp_path / "run"
    run.mkdir()
    existing = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start")
    assert existing.returncode == 2
    assert json_result(existing)["blocking_reasons"] == ["state.run_exists"]

    run.rmdir()
    started = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start")
    assert started.returncode == 0
    other_repo = tmp_path / "other-repo"
    other_repo.mkdir()
    mismatch = invoke(skill, other_repo, "--run-dir", str(run), "--format", "json", "status")
    assert mismatch.returncode == 2
    assert json_result(mismatch)["blocking_reasons"] == ["state.identity_mismatch"]


def test_rejects_symlink_escape_into_installed_skill(tmp_path: Path) -> None:
    skill = create_skill(tmp_path)
    internal = skill / "internal"
    internal.mkdir()
    link = tmp_path / "linked-state"
    try:
        os.symlink(internal, link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    repo = tmp_path / "repo"
    repo.mkdir()
    result = invoke(skill, repo, "--run-dir", str(link / "run"), "--format", "json", "start")
    assert result.returncode == 2
    assert json_result(result)["blocking_reasons"] == ["path.run_dir_in_skill"]


def test_manifest_rejects_unknown_placeholder_and_traversal(tmp_path: Path) -> None:
    payload = manifest()
    payload["commands"]["start"]["steps"][0]["argv"].append("{mystery}")
    payload["artifacts"][0]["path"] = "../escape"
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    result = invoke(skill, repo, "--format", "json", "doctor")
    assert result.returncode == 2
    response = json_result(result)
    assert response["blocking_reasons"] == ["manifest.invalid"]


def test_human_failure_uses_stderr_without_traceback(tmp_path: Path) -> None:
    skill = create_skill(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    result = invoke(skill, repo, "status")
    assert result.returncode == 2
    assert "state.invalid" in result.stderr or "path.run_dir_required" in result.stderr
    assert "Traceback" not in result.stderr


def test_child_failure_and_invalid_diagnostic_json_are_actionable(tmp_path: Path) -> None:
    payload = manifest()
    payload["commands"]["validate"]["steps"][0]["diagnostics_json"] = True
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    assert invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start").returncode == 0
    (skill / "scripts" / "workflow.py").write_text(
        "print('{not-json')\nraise SystemExit(1)\n",
        encoding="utf-8",
    )
    result = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "validate")
    assert result.returncode == 4
    response = json_result(result)
    assert response["blocking_reasons"] == ["adapter.validate_failed"]
    assert response["diagnostics"][0]["details"]["returncode"] == 1


def test_noncanonical_child_diagnostic_is_rejected_with_local_repair(tmp_path: Path) -> None:
    payload = manifest()
    payload["commands"]["validate"]["steps"][0]["diagnostics_json"] = True
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    assert invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start").returncode == 0
    (skill / "scripts" / "workflow.py").write_text(
        "print('{\"diagnostics\":[{\"code\":\"legacy.failure\",\"message\":\"broken\"}]}')\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    result = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "validate")
    assert result.returncode == 4
    diagnostic = json_result(result)["diagnostics"][0]
    assert diagnostic["code"] == "adapter.diagnostic_contract_invalid"
    assert diagnostic["category"] == "contract_contradiction"
    assert diagnostic["path"].endswith("workflow.py")
    assert diagnostic["next_command"]["argv"][1].endswith("workflow.py")


def test_tampered_state_is_rejected(tmp_path: Path) -> None:
    skill = create_skill(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    assert invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start").returncode == 0
    state_path = run / ".skill-cli-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["phase"] = "complete"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "status")
    assert result.returncode == 2
    assert json_result(result)["blocking_reasons"] == ["state.tampered"]


def test_failed_post_finalize_step_does_not_commit_complete_state(tmp_path: Path) -> None:
    payload = manifest()
    capture = payload["commands"]["finalize"]["steps"][0]
    capture["capture_stdout"] = "work"
    failing = {
        "argv": ["{python}", "{skill_dir}/scripts/fail.py"],
        "repeat": [],
        "capture_stdout": None,
        "diagnostics_json": False,
        "failure": "operational",
    }
    payload["commands"]["finalize"]["steps"].append(failing)
    skill = create_skill(tmp_path, payload)
    (skill / "scripts" / "fail.py").write_text("raise SystemExit(9)\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    assert invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start").returncode == 0
    assert invoke(skill, repo, "--run-dir", str(run), "--format", "json", "validate").returncode == 0
    result = invoke(skill, repo, "--run-dir", str(run), "--format", "json", "finalize")
    assert result.returncode == 4
    assert json_result(result)["phase"] == "validated"
    state = json.loads((run / ".skill-cli-state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "validated"


def test_stateless_run_returns_inline_result_without_state(tmp_path: Path) -> None:
    payload = {
        "protocol_version": "1.0",
        "mode": "stateless",
        "skill": "fixture-skill",
        "minimum_python": "3.11",
        "run_dir_policy": "outside_skill",
        "requirements": [],
        "inputs": [
            {
                "name": "request",
                "kind": "string",
                "required": True,
                "repeatable": False,
                "description": "Request.",
                "choices": [],
            }
        ],
        "artifacts": [],
        "phases": {},
        "commands": {
            "run": {
                "allowed_phases": [],
                "success_phase": None,
                "steps": [
                    {
                        "argv": ["{python}", "{skill_dir}/scripts/workflow.py", "{input.request}"],
                        "repeat": [],
                        "capture_stdout": None,
                        "diagnostics_json": False,
                        "failure": "blocked",
                    }
                ],
            }
        },
    }
    skill = create_skill(tmp_path, payload)
    (skill / "scripts" / "workflow.py").write_text(
        "import json, sys\nprint(json.dumps({'request': sys.argv[1]}))\n",
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    result = invoke(skill, repo, "--input", "request=route me", "--format", "json", "run")
    response = json_result(result)
    assert result.returncode == 0
    assert response["status"] == "complete"
    assert response["result"] == {"request": "route me"}
    assert not list(tmp_path.rglob(".skill-cli-state.json"))
    unsupported = invoke(skill, repo, "--format", "json", "status")
    assert unsupported.returncode == 3
    assert json_result(unsupported)["blocking_reasons"] == ["command.unsupported"]


def test_custom_next_transition_accepts_late_immutable_input(tmp_path: Path) -> None:
    payload = manifest()
    payload["inputs"].append(
        {
            "name": "decision",
            "kind": "choice",
            "required": False,
            "required_for": ["promote"],
            "repeatable": False,
            "description": "Late phase decision.",
            "choices": ["yes", "no"],
        }
    )
    payload["phases"]["drafting"]["next_command"] = "promote"
    payload["commands"]["promote"] = {
        "when": {"decision": ["yes"]},
        "allowed_phases": ["drafting"],
        "success_phase": "validated",
        "steps": [],
    }
    payload["commands"]["promote"]["steps"] = payload["commands"]["validate"]["steps"]
    skill = create_skill(tmp_path, payload)
    repo = tmp_path / "repo"
    repo.mkdir()
    run = tmp_path / "run"
    assert invoke(skill, repo, "--run-dir", str(run), "--format", "json", "start").returncode == 0
    advanced = invoke(
        skill,
        repo,
        "--run-dir",
        str(run),
        "--input",
        "decision=yes",
        "--format",
        "json",
        "next",
    )
    assert advanced.returncode == 0
    assert json_result(advanced)["phase"] == "validated"
    changed = invoke(
        skill,
        repo,
        "--run-dir",
        str(run),
        "--input",
        "decision=no",
        "--format",
        "json",
        "finalize",
    )
    assert changed.returncode == 3
    assert json_result(changed)["blocking_reasons"] == ["input.immutable"]
