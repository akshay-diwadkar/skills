import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "implement-plan" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from implementation_contract import load_contract, parse_plan, scaffold_bundle  # noqa: E402
from v4_plan_factory import finalized_tiny_plan  # type: ignore[import-not-found]  # noqa: E402


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "eval@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Eval"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=path, check=True)


def v4_repo_plan(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    init_repo(repo)
    plan_path = tmp_path / "plan.md"
    plan_path.write_text(finalized_tiny_plan(repo), encoding="utf-8")
    return repo, plan_path


def test_contract_declares_v4_intake() -> None:
    contract = load_contract()
    assert contract["contract_version"] == 1
    assert contract["supported_plan_contract_versions"] == [4]


def test_finalized_v4_plan_parses_execution_intake(tmp_path: Path) -> None:
    repo, plan_path = v4_repo_plan(tmp_path)
    plan, diagnostics = parse_plan(plan_path.read_text(encoding="utf-8"))
    assert diagnostics == []
    assert plan.contract_version == 4
    assert plan.tier == "tiny"
    assert plan.task_type == "bug-fix"
    assert plan.changes[0]["path"] == "src/names.py"


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_contracts_are_rejected(version: int) -> None:
    plan, diagnostics = parse_plan(f"<!-- plan-contract: {version} -->\n")
    assert plan.contract_version == version
    assert {item.code for item in diagnostics} == {"plan.version.unsupported"}


def test_unfinalized_v4_plan_is_rejected(tmp_path: Path) -> None:
    _, plan_path = v4_repo_plan(tmp_path)
    text = plan_path.read_text(encoding="utf-8").replace("<!-- plan-validation:", "<!-- invalid:")
    _, diagnostics = parse_plan(text)
    assert {item.code for item in diagnostics} == {"plan.receipt"}


def test_scaffold_snapshots_v4_plan_targets_and_dirty_state(tmp_path: Path) -> None:
    repo, plan_path = v4_repo_plan(tmp_path)
    output = repo / ".scratch" / "implement-plan" / "run" / "implementation.json"
    bundle = scaffold_bundle(repo, plan_path, output, "run-1")
    assert bundle["plan"]["contract_version"] == 4
    assert bundle["plan"]["tier"] == "tiny"
    assert bundle["workspace"]["targets"][0]["sha256"]
    assert (output.parent / "plan.md").read_text(encoding="utf-8") == plan_path.read_text(encoding="utf-8")
    assert (output.parent / "baseline" / "src" / "names.py").is_file()


def test_scaffold_rejects_tracked_output(tmp_path: Path) -> None:
    repo, plan_path = v4_repo_plan(tmp_path)
    with pytest.raises(ValueError, match="confirmed ignored"):
        scaffold_bundle(repo, plan_path, repo / "implementation.json", "run-1")


def test_scaffold_cli_writes_json(tmp_path: Path) -> None:
    repo, plan_path = v4_repo_plan(tmp_path)
    output = repo / ".scratch" / "run" / "implementation.json"
    subprocess.run([sys.executable, str(SCRIPTS / "scaffold_implementation.py"), "--repo-root", str(repo), "--plan", str(plan_path), "--output", str(output), "--run-id", "fixture-run"], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["run_id"] == "fixture-run"
