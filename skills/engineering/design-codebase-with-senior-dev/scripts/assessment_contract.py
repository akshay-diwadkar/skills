"""Load and render the canonical design-assessment contract v2."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "assessment-contract.json"

VALIDATION_PREFIX_RE = re.compile(r"^\s*<!--\s*assessment-validation\s*:", re.IGNORECASE)
VALIDATION_RECEIPT_RE = re.compile(
    r"^<!-- assessment-validation: 2; sha256: (?P<digest>[0-9a-f]{64}) -->$"
)


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
    if data.get("contract_version") != 2:
        raise ValueError("assessment contract must have contract_version 2")
    return data


def marker(level: str) -> str:
    if level not in load_contract()["levels"]:
        raise ValueError(f"unsupported level: {level}")
    return f"<!-- design-assessment-contract: 2; level: {level} -->"


def section_names(level: str) -> list[str]:
    contract = load_contract()
    level_contract = contract["levels"].get(level)
    if level_contract is None:
        raise ValueError(f"unsupported level: {level}")
    return [*contract["base_sections"], *level_contract["extra_sections"]]


def _normalized_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").splitlines()


def receipt_lines(text: str) -> list[tuple[int, str]]:
    return [
        (line_number, line.strip())
        for line_number, line in enumerate(_normalized_lines(text), start=1)
        if VALIDATION_PREFIX_RE.match(line)
    ]


def canonical_assessment_body(text: str) -> str:
    """Return LF-normalized assessment content with every validation receipt removed."""
    lines = [line for line in _normalized_lines(text) if not VALIDATION_PREFIX_RE.match(line)]
    return "\n".join(lines).rstrip("\n") + "\n"


def assessment_digest(text: str) -> str:
    return hashlib.sha256(canonical_assessment_body(text).encode("utf-8")).hexdigest()


def validate_receipt(text: str, *, required: bool) -> list[Diagnostic]:
    found = receipt_lines(text)
    if not found:
        return [Diagnostic("finalization.receipt.missing", "Finalized assessment requires one validation receipt")] if required else []
    if len(found) > 1:
        return [Diagnostic("finalization.receipt.duplicate", "Assessment contains multiple validation receipts", found[1][0])]
    line_number, line = found[0]
    match = VALIDATION_RECEIPT_RE.fullmatch(line)
    if match is None:
        return [Diagnostic("finalization.receipt.malformed", "Validation receipt must use the v2 SHA-256 format", line_number)]
    expected = assessment_digest(text)
    if match.group("digest") != expected:
        return [Diagnostic("finalization.receipt.stale", "Validation receipt does not match canonical assessment body", line_number)]
    return []


def finalize_assessment_text(text: str, level: str) -> str:
    body = canonical_assessment_body(text)
    lines = body.rstrip("\n").splitlines()
    receipt = f"<!-- assessment-validation: 2; sha256: {assessment_digest(body)} -->"
    target_marker = marker(level)
    insertion = next(
        (index + 1 for index, line in enumerate(lines) if line.strip() == target_marker),
        None,
    )
    if insertion is None:
        insertion = next(
            (index + 1 for index, line in enumerate(lines) if "design-assessment-contract: 2" in line),
            1,
        )
    lines.insert(insertion, receipt)
    return "\n".join(lines).rstrip("\n") + "\n"


def render_scaffold(level: str, mode: str = "targeted") -> str:
    contract = load_contract()
    if level not in contract["levels"]:
        raise ValueError(f"unsupported level: {level}")

    lines = [
        "# Replace With a Concrete Design Decision",
        marker(level),
        "",
        "## Decision Summary",
        f"- Invocation mode: {mode}",
        "- Selected target: Replace with named module, subsystem, boundary, or candidate",
        f"- Selected level: {level}",
        "- Recommended design: Replace with concise summary of the minimum sufficient design",
        "- Why minimum sufficient: Replace with explanation of why lower level fails and higher level is unnecessary",
        "- Protected behavior and contracts: C-1 preserved",
        "- Primary structural pressure: P-1",
        "- Technical-debt disposition: TD-1 disposition: repay | boundary: Replace",
        "- Residual risk: R-1 low",
        "- Next owner: plan-with-senior-dev",
        "",
        "## Scope and Protected Contracts",
        "- C-1: status: preserved | contract: Replace with an API, schema, event, file, CLI, workflow, or operational promise | authorization: none",
        "- H-1: status: assessment-only | next: finish assessment, plan-with-senior-dev, codebase-issue-auditor, optimize-codebase-with-senior-dev, or implement-with-senior-dev",
        "- A-1: status: none | impact: none | verification: none",
        "- TD-1: type: structural | evidence: F-1 | principal: Replace original shortcut or obsolete constraint | interest: Replace recurring cost | frequency: current | blast-radius: Replace affected modules | disposition: repay | reason: Replace why repay beats alternatives | repayment-boundary: Replace smallest structural change | recurrence-guard: Replace test/lint/gate | revisit-trigger: none",
        "",
        "## Evidence and Current State",
        "- F-1: `path:1` | anchor: `existing_anchor` | observation: Replace with verified current behavior | source: code | strength: direct | freshness: current",
        "- Current flow: Replace with input -> owner -> dependency -> side effect -> observable outcome.",
    ]

    if mode != "targeted":
        lines.extend([
            "",
            "## Target Discovery Candidates",
            "- T-1: target: Replace module/boundary | evidence: F-1 | pressure: Replace structural pressure | affected: C-1 | confidence: high | likely-level: " + level + " | blast-radius: local | product-intent-required: false | status: selected | reason: Strongest repository evidence and highest recurring debt interest.",
        ])

    lines.extend([
        "",
        "## Design Pressures and Classification",
        "- P-1: rank: 1 | evidence: F-1 | pressure: Replace with the structural cause and observed cost.",
        f"- D-1: level: {level} | selected: minimum safe design | because: F-1, P-1 | rejected: a stronger design adds cost.",
        "",
        "## Alternatives and Pattern Decisions",
        "- O-1: level: L0 | selected: no | concepts: none | argument-for: Replace | argument-against: Replace | revisit: Replace",
        "- O-2: level: L1 | selected: no | concepts: Replace | argument-for: Replace | argument-against: Replace | revisit: Replace",
    ])

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
