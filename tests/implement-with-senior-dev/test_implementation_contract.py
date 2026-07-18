import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "implement-with-senior-dev" / "scripts"
PLAN_SCRIPTS = REPO_ROOT / "plan-with-senior-dev" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from implementation_contract import load_contract, parse_plan, scaffold_bundle  # noqa: E402


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "eval@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Eval"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=path, check=True)


def v2_plan(path: str = "src/names.py") -> str:
    return f"""# Return a normalized name
<!-- plan-contract: 2 -->
<!-- tier: tiny; task-type: bug-fix -->

## Outcome and Scope
- SC-1: None returns an empty string.
- In scope: `{path}` normalization.
- Unchanged: Non-null names remain unchanged.

## Evidence Ledger
- F-1: `{path}:1` | anchor: `normalize_name` | observation: The function exists.

## Decisions
- D-1: selected: guard None | because: F-1 | rejected: widen the return type.

## Implementation Specification
- CH-1: `{path}` | anchor: `normalize_name` | status: existing | change: Return an empty string for None and preserve all other values.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Preserve the prior implementation snapshot. |

## Verification
- T-1: given: None | expect: empty string | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: None.
- A1: not-applicable | evidence: Local return guard.
- A2: not-applicable | evidence: No external effect.
- A6: not-applicable | evidence: Focused test.
"""


def test_contract_declares_safety_and_bundle_fields() -> None:
    contract = load_contract()

    assert contract["contract_version"] == 1
    assert "mechanical-propagation" in contract["change_kinds"]
    assert "git restore" in contract["forbidden_automatic_commands"]
    assert "final_workspace" in contract["required_bundle_fields"]


def test_current_planner_tiers_are_classified_from_metadata() -> None:
    for tier in ("tiny", "standard", "high-risk"):
        result = subprocess.run(
            [sys.executable, str(PLAN_SCRIPTS / "scaffold_plan.py"), "--tier", tier, "--task-type", "bug-fix"],
            check=True,
            capture_output=True,
            text=True,
        )
        plan, diagnostics = parse_plan(result.stdout.replace("Replace", "Specify").replace("existing_anchor", "anchor"))

        assert plan.tier == tier
        assert plan.contract_version == 2
        assert not [item for item in diagnostics if item.code in {"plan.tier.marker", "plan.version.marker"}]


def test_current_checker_valid_worked_examples_parse_without_drift() -> None:
    worked_examples = (REPO_ROOT / "plan-with-senior-dev" / "references" / "worked-examples.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```plan\n(.*?)```", worked_examples, re.DOTALL)

    parsed = [parse_plan(block) for block in blocks]

    assert [plan.tier for plan, _ in parsed] == ["tiny", "standard", "high-risk"]
    assert all(diagnostics == [] for _, diagnostics in parsed)


def test_v2_tiny_with_ids_remains_tiny() -> None:
    plan, diagnostics = parse_plan(v2_plan())

    assert diagnostics == []
    assert plan.tier == "tiny"
    assert [item["id"] for item in plan.changes] == ["CH-1"]


def test_strict_legacy_tiny_requires_each_field() -> None:
    plan, diagnostics = parse_plan("# Goal\n\n## Goal\nFix it.\n")

    assert plan.contract_version == "legacy"
    assert {item.code for item in diagnostics} >= {
        "plan.legacy.tiny.scope",
        "plan.legacy.tiny.change",
        "plan.legacy.tiny.verification",
        "plan.legacy.tiny.path",
        "plan.legacy.tiny.command",
    }


def test_legacy_tiny_accepts_concrete_sections() -> None:
    text = """# Fix names

## Outcome
None returns an empty string.

## Scope
Only `src/names.py` changes.

## Change
Guard the existing function.

## Verification
Run `python -m pytest -q`.
"""
    plan, diagnostics = parse_plan(text)

    assert diagnostics == []
    assert plan.tier == "tiny"
    assert plan.changes[0]["path"] == "src/names.py"


def test_scaffold_snapshots_plan_targets_and_dirty_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v2_plan(), encoding="utf-8")
    init_repo(repo)
    output = repo / ".scratch" / "implement-with-senior-dev" / "run" / "implementation.json"

    bundle = scaffold_bundle(repo, plan_path, output, "run-1")

    assert bundle["plan"]["tier"] == "tiny"
    assert bundle["workspace"]["targets"][0]["sha256"]
    assert (output.parent / "plan.md").read_text(encoding="utf-8") == v2_plan()
    assert (output.parent / "baseline" / "src" / "names.py").is_file()


def test_scaffold_rejects_tracked_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v2_plan(), encoding="utf-8")
    init_repo(repo)

    with pytest.raises(ValueError, match="confirmed ignored"):
        scaffold_bundle(repo, plan_path, repo / "implementation.json", "run-1")


def test_scaffold_cli_writes_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v2_plan(), encoding="utf-8")
    init_repo(repo)
    output = repo / ".scratch" / "run" / "implementation.json"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "scaffold_implementation.py"),
            "--repo-root",
            str(repo),
            "--plan",
            str(plan_path),
            "--output",
            str(output),
            "--run-id",
            "fixture-run",
        ],
        check=True,
    )

    assert json.loads(output.read_text(encoding="utf-8"))["run_id"] == "fixture-run"
