import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "implement-with-senior-dev" / "scripts"
DEV_DIR = REPO_ROOT / "tests" / "implement-with-senior-dev"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(DEV_DIR))

from check_implementation import validate_bundle  # noqa: E402
from implementation_contract import scaffold_bundle, sha256_file  # noqa: E402
from test_implementation_contract import init_repo, v2_plan  # noqa: E402


def completed_run(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v2_plan(), encoding="utf-8")
    init_repo(repo)
    output = repo / ".scratch" / "run" / "implementation.json"
    bundle = scaffold_bundle(repo, plan_path, output, "run-1")
    before = sha256_file(source)
    source.write_text("def normalize_name(value):\n    return \"\" if value is None else value\n", encoding="utf-8")
    evidence = output.parent / "verification.txt"
    evidence.write_text("1 passed\n", encoding="utf-8")
    bundle.update(
        {
            "status": "complete",
            "changes": [
                {
                    "id": "E-1",
                    "kind": "planned",
                    "ch_ids": ["CH-1"],
                    "paths": ["src/names.py"],
                    "anchors": ["normalize_name"],
                    "before_sha256": before,
                    "after_sha256": sha256_file(source),
                    "evidence": ["Guard added."],
                    "verification": ["T-1"],
                }
            ],
            "verification": [
                {
                    "id": "V-1",
                    "t_ids": ["T-1"],
                    "command": "python -m pytest -q",
                    "expected": "pass",
                    "exit_code": 0,
                    "status": "passed",
                    "evidence": str(evidence),
                }
            ],
            "unresolved_changes": [],
            "unresolved_tests": [],
            "final_workspace": {
                "changed_paths": ["src/names.py"],
                "preserved_initial_dirty_paths": [],
                "concurrent_modifications": [],
            },
            "report": {"summary": "Implemented CH-1 and verified T-1.", "path": ""},
        }
    )
    return repo, plan_path, output, bundle


def codes(bundle: dict, plan_path: Path, repo: Path) -> set[str]:
    return {item.code for item in validate_bundle(bundle, plan_path.read_text(encoding="utf-8"), repo)}


def test_checker_accepts_complete_reconciled_run(tmp_path: Path) -> None:
    repo, plan_path, _, bundle = completed_run(tmp_path)

    assert validate_bundle(bundle, plan_path.read_text(encoding="utf-8"), repo) == []


def test_checker_rejects_unsafe_verification_command(tmp_path: Path) -> None:
    repo, plan_path, _, bundle = completed_run(tmp_path)
    bundle["verification"][0]["command"] = "git restore src/names.py"

    assert "verification.command.unsafe" in codes(bundle, plan_path, repo)


def test_checker_rejects_undeclared_workspace_path(tmp_path: Path) -> None:
    repo, plan_path, _, bundle = completed_run(tmp_path)
    extra = repo / "extra.txt"
    extra.write_text("unexpected\n", encoding="utf-8")
    bundle["final_workspace"]["changed_paths"].append("extra.txt")

    assert "workspace.path.undeclared" in codes(bundle, plan_path, repo)


def test_checker_requires_all_mechanical_policy_flags(tmp_path: Path) -> None:
    repo, plan_path, _, bundle = completed_run(tmp_path)
    bundle["changes"][0]["kind"] = "mechanical-propagation"
    bundle["changes"][0]["policy"] = {"directly_caused_by_plan": True, "necessary_for": "compile"}

    assert "change.mechanical.policy" in codes(bundle, plan_path, repo)


def test_checker_detects_modified_initial_user_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    notes = repo / "notes.txt"
    notes.write_text("baseline\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v2_plan(), encoding="utf-8")
    init_repo(repo)
    notes.write_text("user work\n", encoding="utf-8")
    bundle = scaffold_bundle(repo, plan_path, repo / ".scratch" / "run" / "implementation.json", "run-1")
    notes.write_text("overwritten\n", encoding="utf-8")

    assert "workspace.dirty.modified" in codes(bundle, plan_path, repo)


def test_checker_allows_blocked_dirty_target_when_no_edit_was_attempted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v2_plan(), encoding="utf-8")
    init_repo(repo)
    source.write_text("def normalize_name(value):\n    return value  # user\n", encoding="utf-8")
    bundle = scaffold_bundle(repo, plan_path, repo / ".scratch" / "run" / "implementation.json", "run-1")
    bundle["status"] = "blocked"
    bundle["report"]["summary"] = "Blocked because the target is dirty."
    bundle["final_workspace"]["preserved_initial_dirty_paths"] = ["src/names.py"]

    assert "workspace.target.dirty" not in codes(bundle, plan_path, repo)


def test_checker_cli_emits_json_diagnostics(tmp_path: Path) -> None:
    repo, plan_path, output, bundle = completed_run(tmp_path)
    bundle["unresolved_changes"] = ["CH-1"]
    output.write_text(json.dumps(bundle), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "check_implementation.py"),
            "--repo-root",
            str(repo),
            "--plan",
            str(plan_path),
            str(output),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["valid"] is False
    assert any(item["code"] == "complete.unresolved" for item in payload["diagnostics"])
