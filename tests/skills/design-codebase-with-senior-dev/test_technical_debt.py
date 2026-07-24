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
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L0").replace("recurrence-guard: unit test", "recurrence-guard:")
    diags = validate(text, "L0", tmp_path)

    assert any(d.code == "tech_debt.recurrence_guard.missing" for d in diags)


def test_accept_disposition_requires_revisit_trigger(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L0").replace("disposition: repay", "disposition: accept").replace("revisit-trigger: none", "revisit-trigger:")
    diags = validate(text, "L0", tmp_path)

    assert any(d.code == "tech_debt.revisit_trigger.missing" for d in diags)


def test_contain_disposition_requires_containment_boundary(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L0").replace("disposition: repay", "disposition: contain")
    diags = validate(text, "L0", tmp_path)

    assert any(d.code == "tech_debt.containment_boundary.missing" for d in diags)


def test_valid_tech_debt_record_passes(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L0")
    diags = validate(text, "L0", tmp_path)

    assert diags == []
