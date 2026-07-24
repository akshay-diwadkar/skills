"""Load and render the canonical design-assessment contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "assessment-contract.json"


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
        raise ValueError("assessment contract must have contract_version 1")
    return data


def marker(level: str) -> str:
    if level not in load_contract()["levels"]:
        raise ValueError(f"unsupported level: {level}")
    return f"<!-- design-assessment-contract: 1; level: {level} -->"


def section_names(level: str) -> list[str]:
    contract = load_contract()
    level_contract = contract["levels"].get(level)
    if level_contract is None:
        raise ValueError(f"unsupported level: {level}")
    return [*contract["base_sections"], *level_contract["extra_sections"]]


def render_scaffold(level: str) -> str:
    contract = load_contract()
    if level not in contract["levels"]:
        raise ValueError(f"unsupported level: {level}")

    lines = [
        "# Replace With a Concrete Design Decision",
        marker(level),
        "",
        "## Scope and Protected Contracts",
        "- C-1: status: preserved | contract: Replace with an API, schema, event, file, CLI, workflow, or operational promise | authorization: none",
        "- H-1: status: assessment-only | next: finish assessment, plan-with-senior-dev, or implement-with-senior-dev",
        "- A-1: status: none | impact: none | verification: none",
        "",
        "## Evidence and Current State",
        "- F-1: `path:1` | anchor: `existing_anchor` | observation: Replace with verified current behavior.",
        "- Current flow: Replace with input -> owner -> dependency -> side effect -> observable outcome.",
        "",
        "## Design Pressures and Classification",
        "- P-1: rank: 1 | evidence: F-1 | pressure: Replace with the structural cause and observed cost.",
        f"- D-1: level: {level} | selected: Replace with the minimum sufficient design | because: F-1, P-1 | rejected: Replace with the nearest lower or stronger level.",
        "",
        "## Alternatives and Pattern Decisions",
        "- O-1: level: L0 | selected: no | concepts: none | argument-for: Replace | argument-against: Replace | revisit: Replace",
        "- O-2: level: L1 | selected: no | concepts: Replace | argument-for: Replace | argument-against: Replace | revisit: Replace",
    ]
    if contract["levels"][level]["minimum_alternatives"] >= 3:
        lines.append("- O-3: level: L2 | selected: no | concepts: Replace | argument-for: Replace | argument-against: Replace | revisit: Replace")
    if contract["levels"][level]["requires_pattern_gate"]:
        answers = ", ".join(f"Q{number}=yes" for number in range(1, 15))
        lines.append(
            "- G-1: pattern: Replace | scope: introduced | result: admit | "
            f"questions: {answers} | evidence: F-1, P-1"
        )
    lines.extend([
        "",
        "## Verification and Residual Risk",
        "- V-1: proves: D-1 | method: Replace with an exact command, test, or manual check | expected: Replace with an observable result.",
        "- R-1: severity: low | scenario: Replace with remaining uncertainty | consequence: Replace | owner: Replace | follow-up: Replace",
    ])

    if level == "L1":
        lines.extend([
            "",
            "## Local Simplification and Preservation",
            "- Responsibility: Replace with the cohesive local owner.",
            "- Concepts removed: Replace or none.",
            "- Concepts retained: Replace.",
            "- Preservation proof: Replace with characterized behavior and V-1.",
        ])
    if level in {"L2", "L3"}:
        lines.extend([
            "",
            "## Target Boundary",
            "- Responsibility and owner: Replace.",
            "- Dependency direction: Replace.",
            "- State and contract ownership: Replace.",
            "- Allowed calls and failures: Replace.",
            "",
            "## Migration and Rollback",
            "- M-1: prerequisite: Replace | changed boundary: Replace | preserved: C-1 | proof: V-1 | rollback trigger: Replace | rollback action: Replace | cleanup: Replace",
            "",
            "## Operational Semantics",
        ])
        lines.extend(f"- {field.title()}: not-applicable: Replace with a concrete reason." for field in contract["operational_fields"])
    if level == "L3":
        lines.extend(["", "## System Ownership and Evolution"])
        lines.extend(f"- {field.title()}: Replace." for field in contract["l3_evolution_fields"])
    return "\n".join(lines).rstrip() + "\n"
