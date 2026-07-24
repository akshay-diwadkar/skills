import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_assessment import validate  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def test_repay_disposition_requires_recurrence_guard(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1").replace("recurrence-guard: unit test", "recurrence-guard: none")
    diags = validate(text, "L1", tmp_path)
    assert any(item.code == "tech_debt.recurrence_guard.missing" for item in diags)


def test_accept_disposition_requires_revisit_trigger(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1").replace("disposition: repay", "disposition: accept").replace("revisit-trigger: none", "revisit-trigger: n/a")
    diags = validate(text, "L1", tmp_path)
    assert any(item.code == "tech_debt.revisit_trigger.missing" for item in diags)


def test_valid_tech_debt_record_passes(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1")
    diags = validate(text, "L1", tmp_path)
    assert diags == []
