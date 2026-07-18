from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "optimize-codebase-with-senior-dev" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from optimization_contract import marker  # noqa: E402


def valid_report(
    scope: str = "targeted",
    stage: str = "plan",
    *,
    investigate: bool = False,
    static: bool = False,
    inconclusive: bool = False,
    note: str = "measured hot path preserves behavior",
) -> str:
    if scope == "sweep":
        coverage = [
            "- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none",
            "- CV-2: subsystem: app | pass: build-test-ci | status: clean | evidence: F-1 | priority: low | resume: none",
            "- CV-3: subsystem: ci | pass: runtime | status: rejected | evidence: F-1 | priority: low | resume: none",
            "- CV-4: subsystem: ci | pass: build-test-ci | status: deferred | evidence: F-1 | priority: high | resume: collect representative CI timing and cache evidence",
        ]
        inventory = ["- Subsystems: app, ci", "- Passes: runtime, build-test-ci", "- Sweep status: incomplete"]
        band = "strategic-win"
        impact, confidence, effort, risk, strength, blast = "high", "high", "medium", "low", "bounded", "medium"
        gates = "target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes"
        experiment = "none"
    else:
        coverage = ["- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none"]
        inventory = ["- Subsystems: app", "- Passes: runtime", "- Sweep status: not-applicable"]
        band = "investigate" if investigate else "quick-win"
        impact, confidence, effort, risk, strength, blast = (
            ("high", "medium", "low", "medium", "bounded", "medium")
            if investigate
            else ("medium", "high", "low", "low", "strong", "low")
        )
        gates = (
            "target=yes, baseline=no, behavior=yes, compatibility=no, verification=yes, rollback=yes, operational-cost=yes, decisions=yes"
            if investigate
            else "target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes"
        )
        experiment = "resolve the version and run a disposable parity benchmark" if investigate else "none"

    authorization = "plan-only" if stage == "plan" else "explicit implementation — user requested candidate C-1"
    baseline_method = "blocked" if investigate else "static" if static else "command"
    baseline_result = (
        "production timing unavailable; safe confirmation defined"
        if investigate
        else "three duplicated policy branches across one change path"
        if static
        else "median 40 ms across five warm runs"
    )
    research_finding = "version-matched research deferred for the confirmation experiment" if investigate else "local change needs no ecosystem capability"
    x_records = [
        "- X-1: target: C-2 | status: rejected | reason: broad cache changes behavior without evidence | evidence: F-1, B-1 | revisit: define freshness and profile cross-call reuse."
    ]
    if investigate:
        x_records.append(
            "- X-2: target: C-1 | status: deferred | reason: baseline and compatibility are not confirmed | evidence: F-1, B-1 | revisit: complete the named experiment."
        )
    if scope == "sweep":
        x_records.append(
            "- X-2: target: CV-4 | status: deferred | reason: CI evidence is unavailable in this wave | evidence: F-1 | revisit: resume with three representative CI runs."
        )

    sections = [
        "# Optimize the Verified Workflow",
        marker(scope, stage),
        "",
        "## Brief and Authorization",
        f"- Scope: {scope}",
        f"- Stage: {stage}",
        f"- Authorization: {authorization}",
        f"- Goal: {note}.",
        "- Protected behavior: Preserve public output, errors, side effects, coverage, and release gates.",
        "",
        "## System and Coverage Map",
        *inventory,
        *coverage,
        "",
        "## Evidence and Baselines",
        "- F-1: `src/system.py:1` | anchor: `current` | observation: The current function owns the measured workflow.",
        f"- B-1: workflow: current operation | method: {baseline_method} | command: run focused benchmark | result: {baseline_result} | confidence: {confidence} | evidence: F-1",
        "",
        "## Capability Research",
        f"- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: {research_finding} | target: B-1 | compatibility: not-applicable",
        "",
        "## Candidate Decisions",
        f"- C-1: band: {band} | impact: {impact} | confidence: {confidence} | effort: {effort} | risk: {risk} | verification-strength: {strength} | blast-radius: {blast} | reversible: yes | independent: yes | gates: {gates} | evidence: F-1, B-1, R-1 | change: optimize one local boundary | benefit: improve the named workflow | verify: V-1 | rollback: restore the previous local implementation | operational-cost: bounded call-scoped memory with no new dependency | experiment: {experiment}",
        "- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | change: rewrite unrelated systems | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: broad migration and ownership | experiment: none",
        "",
        "## Recommended Plan",
        "- Selected candidate: C-1",
        "- Ordered changes: Characterize behavior, change one boundary, run focused tests, and compare the same workload.",
        "- Behavior guardrails: Preserve public contracts, coverage, failure visibility, and operational semantics.",
        f"- H-1: stage: {stage} | next: finish optimization | candidate: C-1",
        "",
        "## Verification, Rollback, and Residual Risk",
        "- V-1: proves: C-1 | method: run focused parity tests and the comparable workflow | expected: identical behavior and the named improvement threshold.",
        "- V-2: proves: C-2 | method: no accepted proof | expected: reject the unrelated rewrite.",
        "- Rollback trigger: Any behavior mismatch or neutral or worse comparable result.",
        "- Rollback action: Restore the previous local implementation and rerun parity tests.",
        "- Residual risk: Production workload variance remains bounded by staged verification.",
        "",
        "## Rejects, Deferrals, and Limitations",
        *x_records,
    ]
    if stage == "implementation":
        execution_result = (
            "parity passed but the 42 ms median is inconclusive; rollback selected"
            if inconclusive
            else "parity passed and median improved"
        )
        after_result = "median 42 ms across five warm runs" if inconclusive else "median 18 ms across five warm runs"
        sections.extend([
            "",
            "## Execution Record",
            f"- E-1: candidate: C-1 | authorization: user requested candidate C-1 | change: applied the local optimization | result: {execution_result} | regression: V-1",
            "",
            "## Before/After Verification",
            f"- B-2: workflow: current operation | method: command | command: run focused benchmark after | result: {after_result} | confidence: high | evidence: F-1",
            "- Comparison: B-1 -> B-2 used the same workload, runtime, cache state, and five-run median.",
        ])
    return "\n".join(sections) + "\n"
