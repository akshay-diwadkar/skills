"""Load and render the canonical optimization contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _diagnostic_contract import normalize_diagnostic

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "references"
CONTRACT_PATH = REFERENCE_DIR / "optimization-contract.json"
HANDOFF_CONTRACT_PATH = REFERENCE_DIR / "handoff-contract.json"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None
    is_warning: bool = False

    def __str__(self) -> str:
        location = f" line {self.line}:" if self.line is not None else ":"
        severity = "warning" if self.is_warning else "error"
        return f"{self.code} ({severity}){location} {self.message}"

    def to_dict(
        self,
        *,
        path: str | Path = "optimization.md",
        next_command: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return normalize_diagnostic(
            {
                "code": self.code,
                "message": self.message,
                "line": self.line,
                "severity": "warning" if self.is_warning else "error",
            },
            skill="optimize-codebase",
            phase="validate",
            artifact="optimization-report",
            path=path,
            next_command=next_command,
        )


def _load(path: Path, version: int, name: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("contract_version") != version:
        raise ValueError(f"{name} contract must have contract_version {version}")
    return data


def load_contract() -> dict[str, Any]:
    return _load(CONTRACT_PATH, 2, "optimization")


def load_handoff_contract() -> dict[str, Any]:
    return _load(HANDOFF_CONTRACT_PATH, 1, "handoff")


def marker(path: str, scope: str, stage: str) -> str:
    contract = load_contract()
    if path not in contract["paths"]:
        raise ValueError(f"unsupported path: {path}")
    if scope not in contract["scopes"] or stage not in contract["stages"]:
        raise ValueError(f"unsupported optimization contract: {path}/{scope}/{stage}")
    return f"<!-- optimization-contract: 2; path: {path}; scope: {scope}; stage: {stage} -->"


def section_names(path: str, stage: str) -> list[str]:
    contract = load_contract()
    if path == "fast":
        return list(contract["fast"]["sections"])
    if path != "full" or stage not in contract["stages"]:
        raise ValueError(f"unsupported optimization contract: {path}/{stage}")
    return [*contract["full"]["base_sections"], *contract["full"]["stage_sections"][stage]]


def render_scaffold(path: str, scope: str, stage: str) -> str:
    contract = load_contract()
    if path == "fast":
        if scope != contract["fast"]["scope"] or stage != contract["fast"]["stage"]:
            raise ValueError("fast path requires targeted scope and implementation stage")
        eligibility = ", ".join(f"{name}=yes" for name in contract["fast"]["eligibility"])
        return "\n".join(
            [
                "# Replace With the Authorized Quick Win",
                marker(path, scope, stage),
                "",
                "## Fast Path Decision",
                "- Authorization: explicit implementation — replace with the current user request",
                "- F-1: `path:1` | anchor: `existing_symbol` | observation: Replace with the verified single-symbol fact.",
                "- B-1: workflow: Replace | method: command | command: Replace | result: Replace with raw measured or bounded-static evidence | confidence: high | evidence: F-1",
                f"- C-1: band: quick-win | eligibility: {eligibility} | evidence: F-1, B-1 | anchors: path:existing_symbol | change: Replace with one mechanism | benefit: Replace with the acceptance threshold | verify: Replace with the exact post-change command | expected: Replace with the observable result | rollback: Replace with the executable reversal",
                "",
            ]
        )

    if path != "full":
        raise ValueError(f"unsupported path: {path}")
    authorization = "plan-only" if stage == "plan" else "explicit implementation — replace with the user's authorization"
    sweep_status = "not-applicable" if scope == "targeted" else "incomplete"
    lines = [
        "# Replace With a Concrete Optimization Decision",
        marker(path, scope, stage),
        "",
        "## Brief and Authorization",
        f"- Scope: {scope}",
        f"- Stage: {stage}",
        f"- Authorization: {authorization}",
        "- Goal: Replace with the named workflow and observable improvement.",
        "- Success criteria: Replace with a measurable threshold.",
        "- Constraints: Replace or none.",
        "- Exclusions: Replace or none.",
        "- Protected behavior: Replace with preserved APIs, outputs, errors, side effects, and operational promises.",
        "",
        "## System and Coverage Map",
        "- Subsystems: Replace with comma-separated stable subsystem IDs.",
        "- Passes: Replace with comma-separated applicable optimization passes.",
        f"- Sweep status: {sweep_status}",
        "- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none",
        "",
        "## Evidence and Baselines",
        "- F-1: `path:1` | anchor: `existing_anchor` | observation: Replace with verified current behavior.",
        "- B-1: workflow: Replace | method: command | command: Replace | result: Replace with raw evidence | confidence: high | evidence: F-1",
        "",
        "## Capability Research",
        "- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: No ecosystem claim is required | target: B-1 | compatibility: not-applicable",
        "",
        "## Candidate Decisions",
        "- C-1: band: strategic-win | impact: high | confidence: high | effort: medium | risk: low | verification-strength: strong | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: path:existing_anchor | change: Replace | benefit: Replace | verify: V-1 | rollback: Replace | operational-cost: Replace | experiment: none",
        "",
        "## Recommended Plan",
        "- Selected candidate: C-1",
        "- Ordered changes: Replace with dependency-ordered file and symbol work.",
        "- Behavior guardrails: Replace with preserved contracts and stop conditions.",
        f"- H-1: stage: {stage} | next: plan-change | candidate: C-1",
        "",
        "## Verification, Rollback, and Residual Risk",
        "- V-1: proves: C-1 | method: Replace with an exact command, test, or manual check | expected: Replace with an observable result.",
        "- Rollback trigger: Replace with the exact threshold or regression signal.",
        "- Rollback action: Replace with an executable reversal.",
        "- Residual risk: Replace or none with evidence.",
        "",
        "## Rejects, Deferrals, and Limitations",
        "- X-1: target: C-2 | status: rejected | reason: Replace with why the alternative failed | evidence: F-1 | revisit: Replace with a concrete condition.",
    ]
    if stage == "implementation":
        lines.extend(
            [
                "",
                "## Execution Record",
                "- E-1: candidate: C-1 | authorization: Replace with the explicit request | change: Replace with the applied patch | result: Replace with the observed result | regression: V-1",
                "",
                "## Before/After Verification",
                "- B-2: workflow: Replace | method: command | command: Replace | result: Replace with comparable after evidence | confidence: high | evidence: F-1",
                "- Comparison: B-1 -> B-2 under the same workload, environment, and cache state.",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
