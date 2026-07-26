import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT / "tests"))
from v4_model import validate  # noqa: E402
from v4_plan_factory import finalized_tiny_plan  # type: ignore[import-not-found]  # noqa: E402


def repo_with_source(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "src" / "names.py"
    path.parent.mkdir()
    path.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    return repo


def codes(text: str, repo: Path) -> set[str]:
    return {item.code for item in validate(text, repo, require_finalized=True)}


def test_v4_fact_requires_range_anchor_and_fingerprints(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    plan = finalized_tiny_plan(repo).replace(" | anchor: `normalize_name`", "", 1)
    assert "evidence.format" in codes(plan, repo)


def test_v4_decision_requires_evidence_and_drawback(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    plan = finalized_tiny_plan(repo).replace(" | drawback: callers require strings.", "")
    assert "decision.evidence" in codes(plan, repo)


def test_v4_change_requires_evidence_ownership(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    plan = finalized_tiny_plan(repo).replace(" | evidence: F-1 | change: return", " | change: return")
    assert "change.format" in codes(plan, repo)


def test_v4_attacks_are_required(tmp_path: Path) -> None:
    repo = repo_with_source(tmp_path)
    plan = finalized_tiny_plan(repo).replace("- A-boundary-input: repaired | evidence: T-1.\n", "")
    assert "attack.missing" in codes(plan, repo)
