import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev"
FINALIZER = SKILL / "scripts" / "finalize_plan.py"
CHECKER = SKILL / "scripts" / "check_plan.py"
EXAMPLES = SKILL / "references" / "worked-examples.md"
FIXTURES = REPO_ROOT / "tests" / "skills" / "plan-with-senior-dev" / "fixtures"
TIERS = ("tiny", "standard", "high-risk")


def example(tier: str) -> str:
    blocks = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)
    return blocks[TIERS.index(tier)]


def finalize(text: str, tier: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FINALIZER), "--tier", tier, "--repo-root", str(FIXTURES / tier), "-"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_finalizer_emits_only_valid_stamped_plan() -> None:
    draft = re.sub(r"^<!-- plan-validation:.*\n", "", example("standard"), flags=re.MULTILINE)
    result = finalize(draft, "standard")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert len(re.findall(r"^<!-- plan-validation: 3; sha256: [0-9a-f]{64} -->$", result.stdout, re.MULTILINE)) == 1
    checked = subprocess.run(
        [sys.executable, str(CHECKER), "--tier", "standard", "--repo-root", str(FIXTURES / "standard"), "--require-finalized", "-"],
        input=result.stdout,
        text=True,
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stdout


def test_finalizer_failure_has_no_stdout() -> None:
    invalid = example("standard").replace("<!-- plan-contract: 3 -->", "<!-- plan-contract: 2 -->")
    result = finalize(invalid, "standard")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "contract.version.unsupported" in result.stderr


def test_receipt_detects_post_validation_edit_and_duplicates() -> None:
    valid = example("tiny")
    stale = valid.replace("empty string", "blank string", 1)
    checked = subprocess.run(
        [sys.executable, str(CHECKER), "--tier", "tiny", "--repo-root", str(FIXTURES / "tiny"), "--require-finalized", "-", "--format", "json"],
        input=stale,
        text=True,
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 1
    assert "finalization.receipt.stale" in checked.stdout

    duplicate = valid.replace("<!-- plan-validation:", "<!-- plan-validation: 3; sha256: " + "0" * 64 + " -->\n<!-- plan-validation:", 1)
    checked = subprocess.run(
        [sys.executable, str(CHECKER), "--tier", "tiny", "--repo-root", str(FIXTURES / "tiny"), "--require-finalized", "-", "--format", "json"],
        input=duplicate,
        text=True,
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 1
    assert "finalization.receipt.duplicate" in checked.stdout


def test_unstamped_plan_fails_only_when_finalized_form_is_required() -> None:
    draft = re.sub(r"^<!-- plan-validation:.*\n", "", example("tiny"), flags=re.MULTILINE)
    ordinary = subprocess.run(
        [sys.executable, str(CHECKER), "--tier", "tiny", "--repo-root", str(FIXTURES / "tiny"), "-"],
        input=draft,
        text=True,
        capture_output=True,
        check=False,
    )
    required = subprocess.run(
        [sys.executable, str(CHECKER), "--tier", "tiny", "--repo-root", str(FIXTURES / "tiny"), "--require-finalized", "-"],
        input=draft,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ordinary.returncode == 0
    assert required.returncode == 1
    assert "finalization.receipt.missing" in required.stdout


def test_malformed_receipt_is_rejected_by_checker_and_finalizer() -> None:
    malformed = re.sub(
        r"^<!-- plan-validation:.*$",
        "<!-- plan-validation: 3; sha256: not-a-digest -->",
        example("tiny"),
        count=1,
        flags=re.MULTILINE,
    )
    result = finalize(malformed, "tiny")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "finalization.receipt.malformed" in result.stderr
