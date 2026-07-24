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
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1", mode="autonomous-discovery")
    diags = validate(text, "L1", tmp_path)
    assert diags == []


def test_autonomous_mode_blocks_low_confidence(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("confidence: high", "confidence: low")
    diags = validate(text, "L1", tmp_path)
    assert any(item.code == "discovery.autonomous.low_confidence_blocked" for item in diags)


def test_autonomous_mode_blocks_product_intent_required(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1", mode="autonomous-discovery").replace("product-intent-required: false", "product-intent-required: true")
    diags = validate(text, "L1", tmp_path)
    assert any(item.code == "discovery.autonomous.product_intent_blocked" for item in diags)


def test_discovery_only_mode_prohibits_selected_target(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    text = valid_v2_assessment("L1", mode="discovery-only")
    # Add a selected target candidate to discovery-only mode to trigger failure
    text_with_selected = text + "\n- T-1: target: src/system.py | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: L1 | blast-radius: local | product-intent-required: false | status: selected | reason: Incorrectly selected\n"
    diags = validate(text_with_selected, "L1", tmp_path)
    assert any(item.code == "discovery.only.selected_prohibited" for item in diags)
