import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT / "tests"))
from plan_contract import load_contract, section_names  # noqa: E402
from v4_model import validate  # noqa: E402
from v4_plan_factory import finalized_tiny_plan  # type: ignore[import-not-found]  # noqa: E402


def source_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "src" / "names.py"
    path.parent.mkdir()
    path.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    return repo


def codes(text: str, repo: Path) -> set[str]:
    return {item.code for item in validate(text, repo, require_finalized=True)}


def test_contract_declares_v4_sections_and_classification() -> None:
    contract = load_contract()
    assert contract["contract_version"] == 4
    assert section_names("tiny") == contract["base_sections"]
    assert set(contract["intents"]) == {"feature", "bug-fix", "refactor"}


def test_finalized_plan_has_valid_v4_shape(tmp_path: Path) -> None:
    repo = source_repo(tmp_path)
    assert not codes(finalized_tiny_plan(repo), repo)


def test_v4_marker_must_be_unique(tmp_path: Path) -> None:
    repo = source_repo(tmp_path)
    assert "contract.marker" in codes(finalized_tiny_plan(repo).replace("<!-- plan-contract: 4 -->", "<!-- plan-contract: 4 -->\n<!-- plan-contract: 4 -->"), repo)


def test_observable_success_criteria_are_required(tmp_path: Path) -> None:
    repo = source_repo(tmp_path)
    plan = finalized_tiny_plan(repo).replace("given: a missing name | when: normalize_name runs | then: it returns an empty string | unchanged: valid strings preserve normalization", "returns an empty string")
    assert "success.observable" in codes(plan, repo)
