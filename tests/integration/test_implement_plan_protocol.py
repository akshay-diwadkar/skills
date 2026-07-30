from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLAN_SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
IMPLEMENT_SKILL = ROOT / "skills" / "engineering" / "implement-plan"
IMPLEMENT_SCRIPTS = IMPLEMENT_SKILL / "scripts"
CLI = IMPLEMENT_SCRIPTS / "cli.py"

sys.path.insert(0, str(PLAN_SCRIPTS))
from plan_runtime import finalized_text, parse_plan  # type: ignore[import-not-found] # noqa: E402

HELPER_SPEC = importlib.util.spec_from_file_location(
    "protocol_hardening_helpers",
    ROOT / "tests" / "skills" / "plan-change" / "hardening_helpers.py",
)
assert HELPER_SPEC and HELPER_SPEC.loader
HELPERS = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPERS)

sys.path.insert(0, str(IMPLEMENT_SCRIPTS))
from implementation_contract import repository_state, sha256_file  # type: ignore[import-not-found] # noqa: E402


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _prepared(
    tmp_path: Path,
    *,
    dirty_target: bool = False,
    dirty_unrelated: bool = False,
) -> tuple[Path, Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = HELPERS.hydrated_scaffold(ROOT, repo, "tiny", [])
    (repo / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    if dirty_unrelated:
        (repo / "notes.txt").write_text("preserve me\n", encoding="utf-8")
    if dirty_target:
        target = repo / "src" / "target.py"
        old_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        target.write_text(
            "def target(raw: str) -> str:\n    return raw.strip()  # user work\n",
            encoding="utf-8",
        )
        draft = draft.replace(old_digest, hashlib.sha256(target.read_bytes()).hexdigest())
    plan = tmp_path / "plan.md"
    plan.write_text(finalized_text(draft, repo), encoding="utf-8")
    return repo, plan, draft


def _invoke(repo: Path, run: Path, plan: Path, command: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(repo),
            "--run-dir",
            str(run),
            "--input",
            f"plan_file={plan}",
            "--format",
            "json",
            command,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stderr == ""
    return result, json.loads(result.stdout)


def _complete(repo: Path, bundle: dict[str, Any], plan_text: str) -> None:
    target = repo / "src" / "target.py"
    before = bundle["workspace"]["targets"][0]["before_sha256"]
    target.write_text("def target(raw: str) -> str:\n    return '' if not raw else raw.strip()\n")
    plan, diagnostics = parse_plan(plan_text)
    assert plan and not diagnostics
    bundle["status"] = "complete"
    bundle["changes"] = [
        {
            "kind": "planned",
            "ch_ids": ["CH-1"],
            "paths": ["src/target.py"],
            "anchors": ["target"],
            "before_sha256": {"src/target.py": before},
            "after_sha256": {"src/target.py": sha256_file(target)},
            "evidence": ["F-1"],
            "verification": ["T-1"],
        }
    ]
    bundle["verification"] = [
        {
            "t_ids": ["T-1"],
            "command": plan.records["T"][0].fields["command"],
            "expected": plan.records["T"][0].fields["then"],
            "exit_code": 0,
            "status": "passed",
            "evidence": "focused test output",
        }
    ]
    bundle["quality_checks"] = [
        {
            "tool": "ruff",
            "command": "ruff check src/target.py",
            "exit_code": 0,
            "status": "passed",
            "evidence": "ruff output",
            "paths": ["src/target.py"],
            "file_sha256": {"src/target.py": sha256_file(target)},
            "checklist_section": ["1", "2"],
        }
    ]
    state = repository_state(repo)
    bundle["final_workspace"] = {
        "git_head": state["git_head"],
        "status": state["status"],
        "changed_paths": sorted(state["status"]),
        "dirty": state["dirty"],
    }
    bundle["report"] = {"summary": "Implemented CH-1 and passed T-1."}


def test_implementation_common_cli_success_and_phase_gates(tmp_path: Path) -> None:
    repo, plan, _draft = _prepared(tmp_path, dirty_unrelated=True)
    unrelated_before = hashlib.sha256((repo / "notes.txt").read_bytes()).hexdigest()
    run = tmp_path / "run"
    started_result, started = _invoke(repo, run, plan, "start")
    assert started_result.returncode == 0
    assert started["phase"] == "implementing"
    assert started["next_command"]["argv"][1] == str(CLI)

    premature_result, premature = _invoke(repo, run, plan, "finalize")
    assert premature_result.returncode == 3
    assert premature["blocking_reasons"] == ["phase.command_forbidden"]

    blocked_result, blocked = _invoke(repo, run, plan, "next")
    assert blocked_result.returncode == 3
    assert blocked["phase"] == "implementing"
    assert "bundle.incomplete" in blocked["blocking_reasons"]

    bundle_path = run / "implementation.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    _complete(repo, bundle, plan.read_text(encoding="utf-8"))
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")

    validated_result, validated = _invoke(repo, run, plan, "next")
    assert validated_result.returncode == 0
    assert validated["phase"] == "validated"
    finalized_result, finalized = _invoke(repo, run, plan, "next")
    assert finalized_result.returncode == 0
    assert finalized["phase"] == "complete"
    receipt = json.loads(bundle_path.read_text(encoding="utf-8"))["validation_receipt"]
    assert receipt["implementation_contract"] == 3
    assert receipt["plan_contract"] == 5
    assert hashlib.sha256((repo / "notes.txt").read_bytes()).hexdigest() == unrelated_before


def test_implementation_start_blocks_invalid_unfinalized_stale_and_dirty_targets(
    tmp_path: Path,
) -> None:
    cases = ("invalid", "unfinalized", "stale", "dirty")
    for case in cases:
        case_root = tmp_path / case
        case_root.mkdir()
        repo, plan, draft = _prepared(case_root, dirty_target=case == "dirty")
        if case == "invalid":
            plan.write_text("not a plan\n", encoding="utf-8")
        elif case == "unfinalized":
            plan.write_text(draft, encoding="utf-8")
        elif case == "stale":
            (repo / "src" / "target.py").write_text("def target(raw: str) -> str:\n    return raw\n")
        before = {
            path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in repo.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }
        run = case_root / "run"
        result, response = _invoke(repo, run, plan, "start")
        assert result.returncode == 3
        assert response["status"] == "blocked"
        assert not run.exists()
        after = {
            path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in repo.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }
        assert after == before
        if case == "dirty":
            assert response["blocking_reasons"] == ["bundle.dirty_target"]
