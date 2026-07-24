import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_assessment import validate  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def test_autonomous_mode_requires_selected_candidate(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    # Change selected candidate status to deferred
    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("status: selected", "status: deferred")
    diags = validate(text, "L1", tmp_path)

    assert any(d.code == "discovery.autonomous.selected_count_invalid" for d in diags)


def test_autonomous_mode_blocks_low_confidence(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("confidence: high", "confidence: low")
    diags = validate(text, "L1", tmp_path)

    assert any(d.code == "discovery.autonomous.low_confidence" for d in diags)


def test_autonomous_mode_blocks_product_intent_required(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("product-intent-required: false", "product-intent-required: true")
    diags = validate(text, "L1", tmp_path)

    assert any(d.code == "discovery.autonomous.product_intent_required" for d in diags)


def test_discovery_only_mode_prohibits_selected_target(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L0", mode="discovery-only").replace("status: deferred", "status: selected")
    diags = validate(text, "L0", tmp_path)

    assert any(d.code == "discovery.only.selected_prohibited" for d in diags)


def test_discovery_only_mode_requires_codebase_issue_auditor_handoff(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L0", mode="discovery-only").replace("next: codebase-issue-auditor", "next: plan-with-senior-dev")
    diags = validate(text, "L0", tmp_path)

    assert any(d.code == "discovery.only.handoff_invalid" for d in diags)
