import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "plan-with-senior-dev" / "scripts" / "check_plan.py"
EXAMPLES = REPO_ROOT / "plan-with-senior-dev" / "references" / "worked-examples.md"
FIXTURES = REPO_ROOT / "tests" / "plan-with-senior-dev" / "fixtures"
TIERS = ("tiny", "standard", "high-risk")


def example_plan(tier: str) -> str:
    blocks = re.findall(r"```plan\n(.*?)\n```", EXAMPLES.read_text(encoding="utf-8"), re.DOTALL)
    return blocks[TIERS.index(tier)]


def run_checker(text: str, tier: str, repo_root: Path | None = None, cwd: Path = REPO_ROOT) -> tuple[int, dict]:
    command = [sys.executable, str(CHECKER), "--tier", tier, "-", "--format", "json"]
    if repo_root is not None:
        command.extend(["--repo-root", str(repo_root)])
    result = subprocess.run(command, input=text, text=True, capture_output=True, cwd=cwd, check=False)
    return result.returncode, json.loads(result.stdout)


def test_every_published_example_passes_repository_aware_validation() -> None:
    for tier in TIERS:
        code, output = run_checker(example_plan(tier), tier, FIXTURES / tier)
        assert code == 0, output
        assert output["passed"] is True
        assert output["contract_version"] == 2
        assert output["coverage"]["grounded_facts"] == output["coverage"]["facts"]
        assert output["coverage"]["grounded_citations"] == output["coverage"]["citations"]


def test_repo_root_defaults_to_current_directory() -> None:
    code, output = run_checker(example_plan("tiny"), "tiny", cwd=FIXTURES / "tiny")
    assert code == 0, output


def test_unrelated_fact_anchor_is_rejected() -> None:
    plan = example_plan("standard").replace("anchor: `_cache`", "anchor: `imaginary_cache`")
    code, output = run_checker(plan, "standard", FIXTURES / "standard")
    assert code == 1
    assert any(item["code"] == "semantic.evidence.anchor_mismatch" for item in output["errors"])


def test_nonexistent_existing_change_symbol_is_rejected() -> None:
    plan = example_plan("standard").replace("anchor: `_cache` | status: existing", "anchor: `imaginary_cache` | status: existing", 1)
    code, output = run_checker(plan, "standard", FIXTURES / "standard")
    assert code == 1
    assert any(item["code"] == "semantic.change.missing_anchor" for item in output["errors"])


def test_existing_change_anchor_requires_matching_grounded_fact() -> None:
    plan = example_plan("standard").replace(
        "anchor: `_cache` | status: existing",
        "anchor: `load_flags` | status: existing",
        1,
    )
    code, output = run_checker(plan, "standard", FIXTURES / "standard")
    assert code == 1
    assert any(item["code"] == "semantic.change.ungrounded_anchor" for item in output["errors"])


def test_keyword_shaped_legacy_plan_is_rejected_with_migration_command() -> None:
    legacy = "# Fix imaginary production outage now\n## Goal\nReturns green\n## Current State\nfile.py:1\n## Change\nFix it\n"
    code, output = run_checker(legacy, "standard", FIXTURES / "standard")
    assert code == 1
    version = next(item for item in output["errors"] if item["code"] == "contract.version.legacy")
    assert "scaffold_plan.py" in version["message"]


def test_high_risk_coverage_counts_severity_qualified_risk_ids() -> None:
    code, output = run_checker(example_plan("high-risk"), "high-risk", FIXTURES / "high-risk")
    assert code == 0, output
    assert output["coverage"]["risks"] == 1
