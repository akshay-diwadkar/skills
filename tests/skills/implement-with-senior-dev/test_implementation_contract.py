import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "implement-with-senior-dev" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _plan_utils import finalize_plan_text  # noqa: E402
from implementation_contract import load_contract, parse_plan, scaffold_bundle  # noqa: E402


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "eval@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Eval"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=path, check=True)


def v3_plan(path: str = "src/names.py") -> str:
    draft = f"""# Return a normalized name
<!-- plan-contract: 3 -->
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
    return finalize_plan_text(draft)


def test_contract_declares_safety_and_bundle_fields() -> None:
    contract = load_contract()

    assert contract["contract_version"] == 1
    assert contract["supported_plan_contract_versions"] == [3]
    assert "mechanical-propagation" in contract["change_kinds"]
    assert "git restore" in contract["forbidden_automatic_commands"]
    assert "final_workspace" in contract["required_bundle_fields"]


def test_v3_worked_examples_pass_intake() -> None:
    worked_examples = (REPO_ROOT / "skills" / "engineering" / "plan-with-senior-dev" / "references" / "worked-examples.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```plan\n(.*?)```", worked_examples, re.DOTALL)

    parsed = [parse_plan(block) for block in blocks]

    assert len(parsed) == 3
    assert all(plan.contract_version == 3 for plan, _ in parsed)
    assert all(diagnostics == [] for _, diagnostics in parsed)


def test_v2_and_legacy_plans_are_rejected() -> None:
    v2_text = """# Return a normalized name
<!-- plan-contract: 2 -->
<!-- tier: tiny; task-type: bug-fix -->
## Outcome and Scope
- SC-1: Test
## Implementation Specification
- CH-1: `src/a.py` | anchor: `a` | status: existing | change: change
## Traceability
| SC-1 | CH-1 | T-1 | None |
## Verification
- T-1: given: a | expect: b | command: `pytest`
"""
    plan, diagnostics = parse_plan(v2_text)
    assert plan.contract_version == 2
    assert {item.code for item in diagnostics} == {"plan.version.unsupported"}

    plan_legacy, diag_legacy = parse_plan("# Legacy Goal\n\n## Goal\nFix it.\n")
    assert plan_legacy.contract_version == "legacy"
    assert {item.code for item in diag_legacy} == {"plan.version.unsupported"}


def test_v3_unfinalized_and_stale_plans_are_rejected() -> None:
    draft = """# Return a normalized name
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: bug-fix -->
## Outcome and Scope
- SC-1: None returns empty.
## Implementation Specification
- CH-1: `src/names.py` | anchor: `normalize_name` | status: existing | change: Fix.
## Traceability
| SC-1 | CH-1 | T-1 | None |
## Verification
- T-1: given: None | expect: empty | command: `pytest`
"""
    plan, diagnostics = parse_plan(draft)
    assert any(diag.code == "finalization.receipt.missing" for diag in diagnostics)

    finalized = finalize_plan_text(draft)
    tampered = finalized.replace("None returns empty", "None returns modified empty")
    plan_tampered, diag_tampered = parse_plan(tampered)
    assert any(diag.code == "finalization.receipt.stale" for diag in diag_tampered)


def test_v3_plan_parses_execution_blueprints() -> None:
    draft = """# Refactor feature
<!-- plan-contract: 3 -->
<!-- tier: standard; task-type: feature -->
## Outcome and Scope
- SC-1: Feature refactored.
## Implementation Specification
- CH-1: `src/core.py` | anchor: `process` | status: existing | change: Update process.

### Execution Blueprint: CH-1 — Workflow control flow
```python
def process(data):
    if not data:
        return None
    return transform(data)
```

## Traceability
| SC-1 | CH-1 | T-1 | Rollback |
## Verification
- T-1: given: input | expect: output | command: `pytest`
"""
    finalized = finalize_plan_text(draft)
    plan, diagnostics = parse_plan(finalized)
    assert diagnostics == []
    assert len(plan.blueprints) == 1
    assert plan.blueprints[0]["changes"] == ["CH-1"]
    assert plan.blueprints[0]["purpose"] == "Workflow control flow"


def test_scaffold_snapshots_plan_targets_and_dirty_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v3_plan(), encoding="utf-8")
    init_repo(repo)
    output = repo / ".scratch" / "implement-with-senior-dev" / "run" / "implementation.json"

    bundle = scaffold_bundle(repo, plan_path, output, "run-1")

    assert bundle["plan"]["contract_version"] == 3
    assert bundle["plan"]["tier"] == "tiny"
    assert bundle["workspace"]["targets"][0]["sha256"]
    assert (output.parent / "plan.md").read_text(encoding="utf-8") == v3_plan()
    assert (output.parent / "baseline" / "src" / "names.py").is_file()


def test_scaffold_rejects_tracked_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "src" / "names.py"
    source.parent.mkdir()
    source.write_text("def normalize_name(value):\n    return value\n", encoding="utf-8")
    plan_path = repo / "plan.md"
    plan_path.write_text(v3_plan(), encoding="utf-8")
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
    plan_path.write_text(v3_plan(), encoding="utf-8")
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
