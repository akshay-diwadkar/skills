import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER = REPO_ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "check_plan.py"
sys.path.insert(0, str(REPO_ROOT / "tests"))
from v4_plan_factory import finalized_tiny_plan  # type: ignore[import-not-found]  # noqa: E402


def repo_with_source(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    return repo


def run_checker(text: str, repo: Path, *, tier: str = "tiny", finalized: bool = True) -> tuple[int, dict]:
    command = [sys.executable, str(CHECKER), "--tier", tier, "--repo-root", str(repo), "--format", "json"]
    if finalized:
        command.append("--require-finalized")
    command.append("-")
    result = subprocess.run(command, input=text, text=True, capture_output=True, check=False)
    return result.returncode, json.loads(result.stdout)


def test_finalized_v4_plan_passes_repository_aware_validation(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    code, output = run_checker(finalized_tiny_plan(repo), repo)
    assert code == 0, output
    assert output == {"valid": True, "contract_version": 4, "diagnostics": []}


def test_cli_tier_mismatch_is_rejected(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    code, output = run_checker(finalized_tiny_plan(repo), repo, tier="standard")
    assert code == 1
    assert any(item["code"] == "metadata.tier.cli_mismatch" for item in output["diagnostics"])


def test_stale_evidence_is_rejected(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    plan = finalized_tiny_plan(repo)
    (repo / "src" / "names.py").write_text("def normalize_name(value):\n    return value.strip()\n", encoding="utf-8")
    code, output = run_checker(plan, repo)
    assert code == 1
    assert {item["code"] for item in output["diagnostics"]} & {"evidence.file_hash", "evidence.excerpt_hash"}


def test_legacy_contract_is_hard_rejected(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    code, output = run_checker("<!-- plan-contract: 3 -->\n", repo, finalized=False)
    assert code == 1
    assert output["diagnostics"][0]["code"] == "contract.marker"
