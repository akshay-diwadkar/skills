import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assessment_contract import finalize_assessment_text, validate_receipt  # noqa: E402
from check_assessment import validate  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def test_finalization_stamps_valid_sha256_receipt(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    draft = valid_v2_assessment("L1")
    assert validate_receipt(draft, required=False) == []
    assert validate_receipt(draft, required=True) != []

    finalized = finalize_assessment_text(draft, "L1")
    assert "<!-- assessment-validation: 2; sha256:" in finalized
    assert validate_receipt(finalized, required=True) == []
    assert validate(finalized, "L1", tmp_path, require_finalized=True) == []


def test_receipt_tampering_is_detected(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")

    draft = valid_v2_assessment("L1")
    finalized = finalize_assessment_text(draft, "L1")

    # Tamper body
    tampered = finalized.replace("src/system.py", "src/modified.py")
    diags = validate_receipt(tampered, required=True)
    assert any(item.code == "finalization.receipt.stale" for item in diags)


def test_duplicate_receipts_are_rejected() -> None:
    draft = valid_v2_assessment("L1")
    finalized = finalize_assessment_text(draft, "L1")
    receipt_line = [line for line in finalized.splitlines() if "assessment-validation" in line][0]
    duplicated = finalized + "\n" + receipt_line + "\n"

    diags = validate_receipt(duplicated, required=True)
    assert any(item.code == "finalization.receipt.duplicate" for item in diags)


def test_malformed_receipt_is_rejected() -> None:
    draft = valid_v2_assessment("L1") + "\n<!-- assessment-validation: 2; sha256: invalid -->\n"
    diags = validate_receipt(draft, required=True)
    assert any(item.code == "finalization.receipt.malformed" for item in diags)
