from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
IMPLEMENT_SCRIPTS = ROOT / "skills" / "engineering" / "implement-plan" / "scripts"
sys.path.insert(0, str(IMPLEMENT_SCRIPTS))
from plan_runtime import finalized_text, parse_plan  # noqa: E402

HELPER_SPEC = importlib.util.spec_from_file_location(
    "hardening_helpers", ROOT / "tests" / "skills" / "plan-change" / "hardening_helpers.py"
)
assert HELPER_SPEC and HELPER_SPEC.loader
HELPERS = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPERS)

import implementation_contract  # noqa: E402
from check_implementation import _implementation_binding_diagnostics, validate_bundle  # noqa: E402
from implementation_contract import (  # noqa: E402
    repository_state,
    scaffold_bundle,
    sha256_file,
    unified_diff_for_change,
)

FINALIZER = IMPLEMENT_SCRIPTS / "finalize_implementation.py"


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _prepared(
    tmp_path: Path,
    *,
    dirty: bool = False,
    tier: str = "tiny",
    domains: list[str] | None = None,
) -> tuple[Path, Path, dict[str, Any], str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = HELPERS.hydrated_scaffold(ROOT, repo, tier, domains or [])
    (repo / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    if dirty:
        (repo / "notes.txt").write_text("initial dirty")
    plan_text = finalized_text(draft, repo)
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(plan_text, encoding="utf-8")
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


def test_complete_bundle_reconciles_actual_workspace(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    assert validate_bundle(bundle, plan_text, repo) == []


def test_strict_common_cli_flags_require_complete_and_receipted_bundle(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    assert {item.code for item in validate_bundle(bundle, plan_text, repo, require_complete=True)} == {
        "bundle.incomplete"
    }
    _complete(repo, bundle, plan_text)
    assert {
        item.code
        for item in validate_bundle(
            bundle,
            plan_text,
            repo,
            require_complete=True,
            require_receipt=True,
        )
    } == {"bundle.receipt"}


def test_plan_sha_nested_rows_and_verification_fail_closed(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["plan"]["sha256"] = "0" * 64
    bundle["changes"][0].pop("anchors")
    bundle["verification"][0]["exit_code"] = 1
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert {"bundle.plan_sha", "bundle.row_required"} <= codes


def test_missing_quality_checks_for_touched_python_fails_closed(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["quality_checks"] = []
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.quality_missing" in codes


def test_failing_ruff_quality_check_fails_closed(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["quality_checks"][0].update({"exit_code": 1, "status": "failed"})
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.quality_failed" in codes


def test_passing_quality_check_with_current_hash_validates(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    assert validate_bundle(bundle, plan_text, repo) == []


def test_tiny_minimal_bundle_profile_validates(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    assert validate_bundle(bundle, plan_text, repo) == []


def test_standard_bundle_requires_distinct_regression_verification(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path, tier="standard")
    _complete(repo, bundle, plan_text)
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.tier_profile" in codes
    bundle["verification"].append(
        {
            "kind": "regression",
            "t_ids": [],
            "command": "python -m pytest -q tests/test_target.py",
            "expected": "affected module regression passes",
            "exit_code": 0,
            "status": "passed",
            "evidence": "regression output",
        }
    )
    assert validate_bundle(bundle, plan_text, repo) == []


def test_high_risk_minimal_bundle_is_under_specified(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(
        tmp_path, tier="high-risk", domains=["security"]
    )
    _complete(repo, bundle, plan_text)
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.tier_profile" in codes


def test_stale_quality_hash_fails_closed(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["quality_checks"][0]["file_sha256"]["src/target.py"] = "0" * 64
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.quality_stale" in codes


def test_exact_preexisting_quality_failure_is_accepted(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    current = bundle["quality_checks"][0]
    bundle["baseline"]["quality_checks"] = [
        {
            **current,
            "exit_code": 1,
            "status": "failed",
            "file_sha256": {"src/target.py": bundle["workspace"]["targets"][0]["before_sha256"]},
        }
    ]
    current.update(
        {
            "exit_code": 1,
            "status": "failed",
            "classification": "pre-existing-failure",
        }
    )
    assert validate_bundle(bundle, plan_text, repo) == []


def test_unknown_baseline_quality_failure_is_rejected(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["quality_checks"][0].update(
        {"exit_code": 1, "status": "failed", "classification": "unknown-baseline"}
    )
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.quality_failed" in codes


def test_unavailable_quality_tool_is_recorded_and_blocking(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    bundle["quality_checks"][0].update(
        {"exit_code": 127, "status": "skipped", "evidence": "ruff executable unavailable"}
    )
    codes = {item.code for item in validate_bundle(bundle, plan_text, repo)}
    assert "bundle.quality_tool_unavailable" in codes


def test_deprecated_plan_contract_scaffolds_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path, _bundle, _plan_text = _prepared(tmp_path)
    contract = implementation_contract.load_contract()
    contract["supported_plan_contract_versions"] = [6]
    contract["deprecated_plan_contract_versions"] = [5]
    monkeypatch.setattr(implementation_contract, "load_contract", lambda: contract)
    deprecated = scaffold_bundle(repo, plan_path, tmp_path / "deprecated.json", "run-deprecated")
    assert deprecated["warnings"] == [
        {
            "code": "bundle.plan_contract_deprecated",
            "severity": "warning",
            "message": "plan-contract v5 is deprecated and will be removed after this release",
        }
    ]


def test_unlisted_plan_contract_hard_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, plan_path, _bundle, _plan_text = _prepared(tmp_path)
    contract = implementation_contract.load_contract()
    contract["supported_plan_contract_versions"] = [6]
    contract["deprecated_plan_contract_versions"] = []
    monkeypatch.setattr(implementation_contract, "load_contract", lambda: contract)
    with pytest.raises(ValueError, match="contract.unsupported"):
        scaffold_bundle(repo, plan_path, tmp_path / "unsupported.json", "run-unsupported")


def test_unified_diff_is_review_only_and_never_validation_authority(tmp_path: Path) -> None:
    repo, _plan_path, bundle, plan_text = _prepared(tmp_path)
    _complete(repo, bundle, plan_text)
    without_diff = validate_bundle(bundle, plan_text, repo)
    generated = unified_diff_for_change(repo, tmp_path / "bundle.json", bundle["changes"][0])
    assert "--- a/src/target.py" in generated
    assert "+++ b/src/target.py" in generated
    bundle["changes"][0]["unified_diff"] = generated
    with_diff = validate_bundle(bundle, plan_text, repo)
    bundle["changes"][0]["unified_diff"] = "deliberately mismatched review metadata"
    mismatched_diff = validate_bundle(bundle, plan_text, repo)
    assert without_diff == with_diff == mismatched_diff == []


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


def test_implementation_revalidates_every_binding_category(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    categories = {
        "evidence": "evidence.py",
        "targets": "target.py",
        "generators": "generate.py",
        "config": "config.toml",
        "schemas": "schema.json",
    }
    binding: dict[str, Any] = {
        "repository_id": str(repo.resolve()),
        **{category: [] for category in categories},
    }
    for category, path in categories.items():
        target = repo / path
        target.write_text(f"{category}\n", encoding="utf-8")
        binding[category].append({"path": path, "sha256": sha256_file(target)})
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    for path in categories.values():
        (repo / path).write_text("stale\n", encoding="utf-8")
    bundle = {"baseline": {"targets": []}, "changes": []}
    codes = {
        item.code
        for item in _implementation_binding_diagnostics(SimpleNamespace(binding=binding), bundle, repo)
    }
    assert {
        "bundle.binding_evidence_stale",
        "bundle.binding_target_stale",
        "bundle.binding_generator_stale",
        "bundle.binding_config_stale",
        "bundle.binding_schema_stale",
    } <= codes
