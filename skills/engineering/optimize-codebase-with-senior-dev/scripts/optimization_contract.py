"""Load and render the canonical optimization contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "optimization-contract.json"


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "severity": "warning" if self.is_warning else "error",
        }


def load_contract() -> dict[str, Any]:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("contract_version") != 1:
        raise ValueError("optimization contract must have contract_version 1")
    return data


def marker(scope: str, stage: str) -> str:
    contract = load_contract()
    if scope not in contract["scopes"]:
        raise ValueError(f"unsupported scope: {scope}")
    if stage not in contract["stages"]:
        raise ValueError(f"unsupported stage: {stage}")
    return f"<!-- optimization-contract: 1; scope: {scope}; stage: {stage} -->"


def section_names(stage: str) -> list[str]:
    contract = load_contract()
    if stage not in contract["stages"]:
        raise ValueError(f"unsupported stage: {stage}")
    return [*contract["base_sections"], *contract["stage_sections"][stage]]


def render_scaffold(scope: str, stage: str) -> str:
    contract = load_contract()
    if scope not in contract["scopes"] or stage not in contract["stages"]:
        raise ValueError(f"unsupported optimization contract: {scope}/{stage}")

    authorization = "plan-only" if stage == "plan" else "explicit implementation — Replace with the user's authorization"
    sweep_status = "not-applicable" if scope == "targeted" else "incomplete"
    lines = [
        "# Replace With a Concrete Optimization Decision",
        marker(scope, stage),
        "",
        "## Brief and Authorization",
        f"- Scope: {scope}",
        f"- Stage: {stage}",
        f"- Authorization: {authorization}",
        "- Goal: Replace with the named workflow and observable improvement.",
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
        "- C-1: band: quick-win | impact: high | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | change: Replace | benefit: Replace | verify: V-1 | rollback: Replace | operational-cost: Replace | experiment: none",
        "",
        "## Recommended Plan",
        "- Selected candidate: C-1",
        "- Ordered changes: Replace with dependency-ordered file and symbol work.",
        "- Behavior guardrails: Replace with preserved contracts and stop conditions.",
        "- H-1: stage: " + stage + " | next: finish optimization | candidate: C-1",
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
        lines.extend([
            "",
            "## Execution Record",
            "- E-1: candidate: C-1 | authorization: Replace with the explicit request | change: Replace with the applied patch | result: Replace with the observed result | regression: V-1",
            "",
            "## Before/After Verification",
            "- B-2: workflow: Replace | method: command | command: Replace | result: Replace with comparable after evidence | confidence: high | evidence: F-1",
            "- Comparison: B-1 -> B-2 under the same workload, environment, and cache state.",
        ])
    return "\n".join(lines).rstrip() + "\n"
