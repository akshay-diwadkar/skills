"""Load and render the handoff-only optimization contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _diagnostic_contract import normalize_diagnostic

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "optimization-contract.json"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    line: int | None = None
    is_warning: bool = False

    def __str__(self) -> str:
        location = f" line {self.line}:" if self.line is not None else ":"
        return f"{self.code} ({'warning' if self.is_warning else 'error'}){location} {self.message}"

    def to_dict(self, *, path: str | Path = "optimization-handoff.md", next_command: dict[str, Any] | None = None) -> dict[str, Any]:
        return normalize_diagnostic(
            {"code": self.code, "message": self.message, "line": self.line, "severity": "warning" if self.is_warning else "error"},
            skill="optimize-codebase",
            phase="validate",
            artifact="optimization-handoff",
            path=path,
            next_command=next_command,
        )


def load_contract() -> dict[str, Any]:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("contract_version") != 2:
        raise ValueError("optimization contract must have contract_version 2")
    return data


def marker(scope: str) -> str:
    if scope not in load_contract()["scopes"]:
        raise ValueError(f"unsupported scope: {scope}")
    return f"<!-- optimization-contract: 2; scope: {scope} -->"


def section_names() -> list[str]:
    return list(load_contract()["full"]["base_sections"])


def render_scaffold(scope: str) -> str:
    sweep_status = "not-applicable" if scope == "targeted" else "incomplete"
    return "\n".join(
        [
            "# Replace With a Concrete Optimization Decision",
            marker(scope),
            "",
            "## Brief and Authorization",
            f"- Scope: {scope}",
            "- Authorization: analysis-only",
            "- Goal: Replace with the named workflow and observable improvement.",
            "- Success criteria: Replace with a measurable threshold.",
            "- Constraints: Replace or none.",
            "- Exclusions: Replace or none.",
            "- Protected behavior: Replace with preserved contracts and side effects.",
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
            "- Planning constraints: Replace with behavior and compatibility constraints for plan-change.",
            "- H-1: next: plan-ready | candidate: C-1",
            "",
            "## Verification, Rollback, and Residual Risk",
            "- V-1: proves: C-1 | method: Replace with a measurement method | expected: Replace with an observable threshold.",
            "- Rollback requirement: Replace with the constraint plan-change must preserve.",
            "- Residual risk: Replace or none with evidence.",
            "",
            "## Rejects, Deferrals, and Limitations",
            "- X-1: target: C-2 | status: rejected | reason: Replace with why the alternative failed | evidence: F-1 | revisit: Replace with a concrete condition.",
            "",
        ]
    )
