import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "engineering" / "plan-change"
FINALIZER = SKILL / "scripts" / "finalize_plan.py"
CHECKER = SKILL / "scripts" / "check_plan.py"
sys.path.insert(0, str(REPO_ROOT / "tests"))
sys.path.insert(0, str(SKILL / "scripts"))
from plan_runtime import repo_snapshot  # noqa: E402
from v4_plan_factory import finalized_tiny_plan  # type: ignore[import-not-found]  # noqa: E402


def repo_with_source(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    return repo


def draft_and_snapshot(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = repo_with_source(tmp_path)
    snapshot = tmp_path / "initial.json"
    snapshot.write_text(json.dumps(repo_snapshot(repo)), encoding="utf-8")
    draft = re.sub(r"^<!-- plan-repository: .* -->\n", "<!-- plan-repository: {} -->\n", finalized_tiny_plan(repo), flags=re.MULTILINE)
    draft = re.sub(r"^<!-- plan-validation:.*\n", "", draft, flags=re.MULTILINE)
    return repo, snapshot, draft


def finalize(repo: Path, snapshot: Path, text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(FINALIZER), "--tier", "tiny", "--repo-root", str(repo), "--initial-state", str(snapshot), "-"], input=text, text=True, capture_output=True, check=False)


def test_finalizer_emits_valid_v4_receipt(tmp_path: Path) -> None:
    repo, snapshot, draft = draft_and_snapshot(tmp_path)
    result = finalize(repo, snapshot, draft)
    assert result.returncode == 0, result.stderr
    assert len(re.findall(r"^<!-- plan-validation: 4; body-sha256: [0-9a-f]{64}; binding-sha256: [0-9a-f]{64} -->$", result.stdout, re.MULTILINE)) == 1
    checked = subprocess.run([sys.executable, str(CHECKER), "--tier", "tiny", "--repo-root", str(repo), "--require-finalized", "--format", "json", "-"], input=result.stdout, text=True, capture_output=True, check=False)
    assert checked.returncode == 0, checked.stdout


def test_finalizer_rejects_legacy_contract(tmp_path: Path) -> None:
    repo, snapshot, _ = draft_and_snapshot(tmp_path)
    result = finalize(repo, snapshot, "<!-- plan-contract: 3 -->\n")
    assert result.returncode == 1
    assert "contract.marker" in result.stderr


def test_finalizer_fails_closed_on_planner_mutation(tmp_path: Path) -> None:
    repo, snapshot, draft = draft_and_snapshot(tmp_path)
    (repo / "planner-created.txt").write_text("mutation\n", encoding="utf-8")
    result = finalize(repo, snapshot, draft)
    assert result.returncode == 1
    assert "planning.worktree_mutated" in result.stderr
