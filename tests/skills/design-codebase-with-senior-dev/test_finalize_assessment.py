import subprocess
import sys
from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEV_DIR.parents[2]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev" / "scripts"
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from assessment_contract import (  # noqa: E402
    assessment_digest,
    canonical_assessment_body,
    finalize_assessment_text,
    render_scaffold,
    validate_receipt,
)
from check_assessment import validate  # noqa: E402
from test_check_assessment import valid_v2_assessment  # noqa: E402


def test_finalization_stamps_valid_sha256_receipt(tmp_path: Path) -> None:
    raw = valid_v2_assessment("L0")
    finalized = finalize_assessment_text(raw, "L0")

    assert "<!-- assessment-validation: 2; level: L0; sha256:" in finalized
    assert validate_receipt(finalized, required=True, expected_level_or_mode="L0") == []


def test_finalization_stamps_discovery_only_receipt(tmp_path: Path) -> None:
    raw = valid_v2_assessment("L0", mode="discovery-only")
    finalized = finalize_assessment_text(raw, "L0", mode="discovery-only")

    assert "<!-- assessment-validation: 2; mode: discovery-only; sha256:" in finalized
    assert validate_receipt(finalized, required=True, expected_level_or_mode="discovery-only") == []


def test_crlf_and_lf_normalization_produces_identical_hash() -> None:
    lf_text = valid_v2_assessment("L1")
    crlf_text = lf_text.replace("\n", "\r\n")

    assert assessment_digest(lf_text) == assessment_digest(crlf_text)
    assert canonical_assessment_body(lf_text) == canonical_assessment_body(crlf_text)


def test_receipt_tampering_is_detected() -> None:
    raw = valid_v2_assessment("L0")
    finalized = finalize_assessment_text(raw, "L0")
    tampered = finalized.replace("minimum safe design", "tampered safe design")

    diags = validate_receipt(tampered, required=True)
    assert any(d.code == "finalization.receipt.stale" for d in diags)


def test_duplicate_receipts_are_rejected() -> None:
    raw = valid_v2_assessment("L0")
    finalized = finalize_assessment_text(raw, "L0")
    duplicate = finalized + "\n<!-- assessment-validation: 2; level: L0; sha256: 0000000000000000000000000000000000000000000000000000000000000000 -->\n"

    diags = validate_receipt(duplicate, required=True)
    assert any(d.code == "finalization.receipt.duplicate" for d in diags)


def test_malformed_receipt_is_rejected() -> None:
    malformed = valid_v2_assessment("L0") + "\n<!-- assessment-validation: 2; invalid: format -->\n"
    diags = validate_receipt(malformed, required=True)

    assert any(d.code == "finalization.receipt.malformed" for d in diags)


def test_receipt_like_text_inside_code_fence_ignored() -> None:
    raw = valid_v2_assessment("L0")
    raw_with_fence = raw + "\n```markdown\n<!-- assessment-validation: 2; level: L0; sha256: fake -->\n```\n"
    finalized = finalize_assessment_text(raw_with_fence, "L0")
    
    diags = validate_receipt(finalized, required=True, expected_level_or_mode="L0")
    assert not diags, f"Expected no receipt errors, got {diags}"


def test_repeated_finalization_is_idempotent() -> None:
    raw = valid_v2_assessment("L0")
    finalized1 = finalize_assessment_text(raw, "L0")
    finalized2 = finalize_assessment_text(finalized1, "L0")

    assert finalized1 == finalized2


def test_finalizer_cli_file_and_stdin_input(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    draft_file = tmp_path / "draft.md"
    draft_file.write_text(valid_v2_assessment("L0"), encoding="utf-8")

    # File input
    res_file = subprocess.run(
        [sys.executable, str(SCRIPTS / "finalize_assessment.py"), str(draft_file), "--level", "L0", "--repo-root", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "<!-- assessment-validation: 2; level: L0; sha256:" in res_file.stdout
    assert validate(res_file.stdout, "L0", tmp_path, require_finalized=True) == []

    # Stdin input
    res_stdin = subprocess.run(
        [sys.executable, str(SCRIPTS / "finalize_assessment.py"), "--level", "L0", "--repo-root", str(tmp_path)],
        input=valid_v2_assessment("L0"),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "<!-- assessment-validation: 2; level: L0; sha256:" in res_stdin.stdout


def test_finalizer_cli_discovery_only_file_and_stdin(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    disc_draft = valid_v2_assessment("L0", mode="discovery-only")
    draft_file = tmp_path / "discovery_draft.md"
    draft_file.write_text(disc_draft, encoding="utf-8")

    # 1. File input with --mode discovery-only
    res_file = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "finalize_assessment.py"),
            str(draft_file),
            "--mode",
            "discovery-only",
            "--repo-root",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "<!-- assessment-validation: 2; mode: discovery-only; sha256:" in res_file.stdout
    assert validate(res_file.stdout, "discovery-only", tmp_path, require_finalized=True) == []

    # 2. Stdin input with --level discovery-only
    res_stdin = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "finalize_assessment.py"),
            "--level",
            "discovery-only",
            "--repo-root",
            str(tmp_path),
        ],
        input=disc_draft,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "<!-- assessment-validation: 2; mode: discovery-only; sha256:" in res_stdin.stdout
    assert validate(res_stdin.stdout, "discovery-only", tmp_path, require_finalized=True) == []


def test_finalizer_cli_invalid_discovery_only_fails(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current(): return 'stable'\n", encoding="utf-8")

    # Invalid discovery-only draft with prohibited decision record
    bad_disc = render_scaffold("L0", mode="discovery-only") + "\n- D-1: level: L0 | selected: foo | because: F-1 | rejected: bar\n"
    draft_file = tmp_path / "bad_discovery.md"
    draft_file.write_text(bad_disc, encoding="utf-8")

    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "finalize_assessment.py"),
            str(draft_file),
            "--mode",
            "discovery-only",
            "--repo-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Cannot finalize invalid assessment draft" in res.stderr
    assert "discovery.only.decision_prohibited" in res.stderr
