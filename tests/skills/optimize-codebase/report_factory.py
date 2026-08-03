from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "optimize-codebase" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from optimization_contract import marker  # noqa: E402


def valid_report(*, status: str = "plan-ready", scope: str = "targeted") -> str:
    band = "investigate" if status == "needs-evidence" else "strategic-win"
    confidence = "medium" if status == "needs-evidence" else "high"
    gates = "target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes"
    if status == "needs-evidence":
        gates = gates.replace("baseline=yes", "baseline=no")
    return f"""# Optimize the Verified Workflow
{marker(scope)}

## Brief and Authorization
- Scope: {scope}
- Authorization: analysis-only
- Goal: Improve the current workflow.
- Success criteria: Preserve output and reduce bounded cost.
- Constraints: No new dependency.
- Exclusions: Unrelated rewrites.
- Protected behavior: Preserve public output, errors, and side effects.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: {'not-applicable' if scope == 'targeted' else 'complete'}
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: The cited function owns the measured workflow.
- B-1: workflow: current operation | method: command | command: run benchmark | result: median 40 ms | confidence: {confidence} | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: No ecosystem claim is required | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: {band} | impact: high | confidence: {confidence} | effort: medium | risk: low | verification-strength: strong | blast-radius: medium | reversible: yes | independent: yes | gates: {gates} | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: optimize one local boundary | benefit: improve the workflow | verify: V-1 | rollback: restore the previous implementation | operational-cost: bounded | experiment: collect a representative baseline
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: rewrite unrelated systems | benefit: unspecified | verify: V-2 | rollback: restore repository | operational-cost: broad | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Planning constraints: Preserve current output and public behavior.
- H-1: next: {status} | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: compare the same workload | expected: identical behavior and lower bounded cost.
- V-2: proves: C-2 | method: no accepted proof | expected: reject the unrelated rewrite.
- Rollback requirement: Preserve a reversible local boundary.
- Residual risk: Workload variance remains.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: broad change lacks evidence | evidence: F-1, B-1 | revisit: define a separate request.
"""


def fixture_repo(path: Path, *, git: bool = False) -> Path:
    (path / "src").mkdir(parents=True)
    (path / "src" / "system.py").write_text("def current():\n    return 1\n", encoding="utf-8")
    if git:
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
        subprocess.run(["git", "add", "."], cwd=path, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=path, check=True, capture_output=True)
    return path


def valid_fast_report() -> str:
    raise ValueError("fast execution was retired")
