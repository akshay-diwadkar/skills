import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO_ROOT / "skills" / "engineering" / "design-codebase-with-senior-dev"
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assessment_contract import (  # noqa: E402
    finalize_assessment_text,
    load_contract,
    marker,
    render_scaffold,
    section_names,
)
from check_assessment import validate  # noqa: E402

LEVELS = ("L0", "L1", "L2", "L3")


def test_contract_declares_exact_sections_for_every_level() -> None:
    contract = load_contract()

    assert contract["contract_version"] == 2
    assert section_names("L0") == contract["base_sections"]
    for level in LEVELS:
        assert section_names(level)[-1] == "Verification and Residual Risk"


def test_scaffold_header_sequence_matches_section_names_exactly() -> None:
    modes = ("targeted", "autonomous-discovery")
    for level in LEVELS:
        for mode in modes:
            scaffold = render_scaffold(level, mode=mode)
            found_headers = [m.group(1).strip() for m in re.finditer(r"^## ([^\n]+)", scaffold, re.MULTILINE)]
            expected_headers = section_names(level, mode=mode)
            assert found_headers == expected_headers, f"Scaffold headers for level={level}, mode={mode} disagree with section_names(): {found_headers} != {expected_headers}"

    scaffold_disc = render_scaffold("L0", mode="discovery-only")
    disc_headers = [m.group(1).strip() for m in re.finditer(r"^## ([^\n]+)", scaffold_disc, re.MULTILINE)]
    expected_disc = section_names("discovery-only", mode="discovery-only")
    assert disc_headers == expected_disc, f"Discovery-only headers disagree: {disc_headers} != {expected_disc}"


def test_scaffold_contains_level_marker_and_required_records() -> None:
    for level in LEVELS:
        scaffold = render_scaffold(level)

        assert marker(level) in scaffold
        assert "<!-- design-assessment-contract: 2;" in scaffold
        assert "## Decision Summary" in scaffold
        assert "- C-1:" in scaffold
        assert "- H-1: status: assessment-only" in scaffold
        assert f"- D-1: level: {level}" in scaffold
        assert "- V-1:" in scaffold


def test_scaffold_cli_prints_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "scaffold_assessment.py"), "--level", "L2"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert marker("L2") in result.stdout
    assert "## Migration and Rollback" in result.stdout
    assert "## System Ownership and Evolution" not in result.stdout


def test_worked_examples_pass_checker_and_finalizer(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)

    billing = tmp_path / "billing"
    billing.mkdir()
    b_lines = ["\n"] * 50
    b_lines[11] = "def render_invoice(): pass\n"
    (billing / "formatter.py").write_text("".join(b_lines), encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    t_lines = ["\n"] * 50
    t_lines[44] = "def test_compact_and_detailed(): pass\n"
    (tests_dir / "test_formatter.py").write_text("".join(t_lines), encoding="utf-8")

    payments = tmp_path / "payments"
    payments.mkdir()
    p_lines = ["\n"] * 50
    p_lines[33] = "import provider_sdk\n"
    (payments / "service.py").write_text("".join(p_lines), encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True)
    sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True)
    real_sha = sha_proc.stdout.strip()

    examples_file = SKILL_DIR / "references" / "worked-examples.md"
    content = examples_file.read_text(encoding="utf-8")
    example_blocks = [("# Assessment:" + block) for block in content.split("# Assessment:") if block.strip() and "<!-- design-assessment-contract:" in block]

    assert len(example_blocks) >= 2, f"Expected at least 2 worked examples, found {len(example_blocks)}"

    for raw_example in example_blocks:
        example = re.sub(r"3a2f1b70298d5c4e90218175f7396781f8084a91", real_sha, raw_example)
        match = re.search(r"level: (L[0-3])", example)
        assert match is not None, f"Example missing level marker:\n{example}"
        level = match.group(1)

        raw_diags = validate(example, level, tmp_path)
        assert raw_diags == [], f"Worked example for {level} failed draft validation:\n{raw_diags}"

        finalized = finalize_assessment_text(example, level)
        final_diags = validate(finalized, level, tmp_path, require_finalized=True)
        assert final_diags == [], f"Worked example for {level} failed finalized validation:\n{final_diags}"
