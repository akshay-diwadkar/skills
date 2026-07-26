from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PLAN_SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
IMPLEMENT_SCRIPTS = ROOT / "skills" / "engineering" / "implement-plan" / "scripts"
sys.path.insert(0, str(PLAN_SCRIPTS))
from plan_runtime import finalized_text, parse_plan  # noqa: E402

HELPER_SPEC = importlib.util.spec_from_file_location(
    "hardening_helpers", ROOT / "tests" / "skills" / "plan-change" / "hardening_helpers.py"
)
assert HELPER_SPEC and HELPER_SPEC.loader
HELPERS = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPERS)

sys.path.insert(0, str(IMPLEMENT_SCRIPTS))
from check_implementation import validate_bundle  # noqa: E402
from implementation_contract import repository_state, scaffold_bundle, sha256_file  # noqa: E402

FINALIZER = IMPLEMENT_SCRIPTS / "finalize_implementation.py"


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _prepared(tmp_path: Path, *, dirty: bool = False) -> tuple[Path, Path, dict[str, Any], str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = HELPERS.hydrated_scaffold(ROOT, repo, "tiny", [])
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    if dirty:
        (repo / "notes.txt").write_text("initial dirty")
    plan_text = finalized_text(draft, repo)
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(plan_text)
    bundle = scaffold_bundle(repo, plan_path, tmp_path / "bundle.json", "run-1")
    return repo, plan_path, bundle, plan_text


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
    state = repository_state(repo)
    bundle["final_workspace"] = {
        "git_head": state["git_head"],
        "status": state["status"],
        "changed_paths": sorted(state["status"]),
        "dirty": state["dirty"],
    }
    bundle["report"] = {"summary": "Implemented CH-1 and passed T-1."}


def test_complete_bundle_reconciles_actual_workspace(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    assert validate_bundle(bundle, plan_text, repo) == []


def test_plan_sha_nested_rows_and_verification_fail_closed(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["plan"]["sha256"] = "0" * 64
    bundle["changes"][0].pop("anchors")
    bundle["verification"][0]["exit_code"] = 1
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert {"bundle.plan_sha", "bundle.row_required"} <= codes


def test_unauthorized_path_and_dirty_file_mutation_are_rejected(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path, dirty=True)
    _complete(repo, bundle, plan_text)
    (repo / "notes.txt").write_text("mutated dirty")
    (repo / "surprise.py").write_text("unexpected = True\n")
    state = repository_state(repo)
    bundle["final_workspace"] = {
        "git_head": state["git_head"],
        "status": state["status"],
        "changed_paths": sorted(state["status"]),
        "dirty": state["dirty"],
    }
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert {"bundle.dirty_preservation", "bundle.unauthorized_path"} <= codes


def test_finalizer_issues_v3_receipt_only_after_full_validation(tmp_path: Path) -> None:
    repo, plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle))
    result = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(repo), "--plan", str(plan_path), str(bundle_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    finalized = json.loads(bundle_path.read_text())
    assert finalized["validation_receipt"]["implementation_contract"] == 3
    body = dict(finalized)
    receipt = body.pop("validation_receipt")
    assert receipt["sha256"] == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_in_progress_bundle_cannot_receive_receipt(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    plan = tmp_path / "plan.md"
    bundle.write_text(json.dumps({"status": "in-progress"}), encoding="utf-8")
    plan.write_text("not consulted", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(tmp_path), "--plan", str(plan), str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "bundle.receipt_status" in result.stdout
    assert "validation_receipt" not in bundle.read_text(encoding="utf-8")
