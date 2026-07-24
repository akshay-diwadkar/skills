"""Load, parse, and render the canonical design-assessment contract v2."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "assessment-contract.json"

VALIDATION_PREFIX_RE = re.compile(r"^\s*<!--\s*assessment-validation\s*:", re.IGNORECASE)
VALIDATION_RECEIPT_RE = re.compile(
    r"^<!-- assessment-validation: 2; (?:level: (?P<level>L[0-3])|mode: (?P<mode>discovery-only)); sha256: (?P<digest>[0-9a-f]{64}) -->$"
)
GIT_HISTORY_LOCATOR_RE = re.compile(r"^git-history:[a-zA-Z0-9_/\.\-]+(?::.+)?$")

VALID_SOURCES = {
    "code",
    "test",
    "fixture",
    "configuration",
    "schema",
    "repository-history",
    "runtime",
    "production",
    "ownership",
    "deployment",
}

VALID_STRENGTHS = {"direct", "corroborated", "inferred"}
VALID_FRESHNESS = {"current", "potentially-stale", "historical"}
VALID_DEBT_TYPES = {"structural", "boundary", "state-ownership", "dependency", "migration", "operational"}
VALID_DEBT_DISPOSITIONS = {"accept", "monitor", "contain", "repay", "retire"}
VALID_HANDOFFS = {
    "finish assessment",
    "plan-with-senior-dev",
    "codebase-issue-auditor",
    "optimize-codebase-with-senior-dev",
    "implement-with-senior-dev",
}
HARD_PATTERN_QUESTIONS = {1, 3, 4, 8, 9, 11, 13, 14}


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


@dataclass
class DecisionSummary:
    mode: str = "targeted"
    target: str = ""
    level: str = "L0"
    recommendation: str = ""
    why_minimum: str = ""
    protected_contracts: str = ""
    primary_pressure: str = ""
    debt_disposition: str | None = None
    residual_risk: str | None = None
    next_owner: str = ""


@dataclass
class FactRecord:
    id: str
    path: str
    line: int
    anchor: str
    observation: str
    source: str = "code"
    strength: str = "direct"
    freshness: str = "current"
    line_number: int = 1


@dataclass
class ExternalFactRecord:
    id: str
    source_id: str
    version: str
    claim: str
    freshness: str = "current"
    relationship: str = "supports"
    authoritative: bool = True
    line_number: int = 1


@dataclass
class TargetCandidateRecord:
    id: str
    target: str
    evidence: list[str]
    pressure: str
    affected: list[str]
    confidence: str
    likely_level: str
    blast_radius: str
    product_intent_required: bool
    rank: int
    status: str  # selected | rejected | deferred
    reason: str
    correctness_risk: str | None = None
    operational_risk: str | None = None
    debt_interest: str | None = None
    change_propagation: str | None = None
    state_ambiguity: str | None = None
    scope_boundedness: str | None = None
    reversibility: str | None = None
    structural_confidence: str | None = None
    line_number: int = 1


@dataclass
class PressureRecord:
    id: str
    rank: int
    evidence: list[str]
    pressure: str
    line_number: int = 1


@dataclass
class ContractRecord:
    id: str
    status: str  # preserved | authorized-change | at-risk
    contract: str
    authorization: str = "none"
    owner: str | None = None
    resolution: str | None = None
    blocking: bool = False
    line_number: int = 1


@dataclass
class DecisionRecord:
    id: str
    level: str
    selected: str
    because: list[str]
    rejected: str
    line_number: int = 1


@dataclass
class AlternativeRecord:
    id: str
    level: str
    selected: bool
    concepts: str
    arg_for: str
    arg_against: str
    revisit: str
    line_number: int = 1


@dataclass
class QuestionAnswer:
    number: int
    answer: str  # yes | no | unknown
    evidence: list[str]
    consequence: str


@dataclass
class PatternGateRecord:
    id: str
    pattern: str
    scope: str  # introduced | removed | retained | rejected | deferred | relied-upon
    result: str  # admit | admit-narrowed | retain | remove | reject | defer
    questions: dict[int, QuestionAnswer] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    removed_destination: str | None = None
    revisit_trigger: str | None = None
    line_number: int = 1


@dataclass
class TechDebtRecord:
    id: str
    type: str  # structural | boundary | state-ownership | dependency | migration | operational
    evidence: list[str]
    principal: str
    interest: str
    frequency: str  # current | recurring | historical | unknown
    blast_radius: str
    disposition: str  # accept | monitor | contain | repay | retire
    reason: str
    repayment_boundary: str
    recurrence_guard: str
    revisit_trigger: str
    containment_boundary: str | None = None
    line_number: int = 1


@dataclass
class VerificationRecord:
    id: str
    proves: list[str]
    method: str
    expected: str
    line_number: int = 1


@dataclass
class MigrationRecord:
    id: str
    prerequisite: str
    changed_boundary: str
    preserved: list[str]
    proof: list[str]
    rollback_trigger: str
    rollback_action: str
    cleanup: str
    line_number: int = 1


@dataclass
class ResidualRiskRecord:
    id: str
    severity: str
    scenario: str
    consequence: str
    owner: str
    follow_up: str
    line_number: int = 1


@dataclass
class AssumptionRecord:
    id: str
    status: str
    impact: str
    verification: str
    line_number: int = 1


@dataclass
class HandoffRecord:
    id: str
    status: str
    next: str
    line_number: int = 1


@dataclass
class Assessment:
    title: str = ""
    contract_version: int = 2
    level: str = "L0"
    mode: str = "targeted"
    decision_summary: DecisionSummary | None = None
    facts: list[FactRecord] = field(default_factory=list)
    external_facts: list[ExternalFactRecord] = field(default_factory=list)
    discovery_candidates: list[TargetCandidateRecord] = field(default_factory=list)
    pressures: list[PressureRecord] = field(default_factory=list)
    contracts: list[ContractRecord] = field(default_factory=list)
    decision: DecisionRecord | None = None
    alternatives: list[AlternativeRecord] = field(default_factory=list)
    pattern_gates: list[PatternGateRecord] = field(default_factory=list)
    tech_debts: list[TechDebtRecord] = field(default_factory=list)
    verifications: list[VerificationRecord] = field(default_factory=list)
    migrations: list[MigrationRecord] = field(default_factory=list)
    residual_risks: list[ResidualRiskRecord] = field(default_factory=list)
    assumptions: list[AssumptionRecord] = field(default_factory=list)
    handoff: HandoffRecord | None = None
    sections: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""
    diagnostics: list[Diagnostic] = field(default_factory=list)


def load_contract() -> dict[str, Any]:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("contract_version") != 2:
        raise ValueError("assessment contract must have contract_version 2")
    return data


def marker(level: str, mode: str = "targeted") -> str:
    if mode == "discovery-only" or level == "discovery-only":
        return "<!-- design-assessment-contract: 2; mode: discovery-only -->"
    if level not in load_contract()["levels"]:
        raise ValueError(f"unsupported level: {level}")
    return f"<!-- design-assessment-contract: 2; level: {level} -->"


def section_names(level: str, mode: str = "targeted") -> list[str]:
    contract = load_contract()
    if mode == "discovery-only" or level == "discovery-only":
        return [
            "Decision Summary",
            "Scope and Protected Contracts",
            "Evidence and Current State",
            "Target Discovery Candidates",
            "Verification and Residual Risk",
        ]
    level_contract = contract["levels"].get(level)
    if level_contract is None:
        raise ValueError(f"unsupported level: {level}")
    names = [*contract["base_sections"], *level_contract["extra_sections"]]
    if mode == "autonomous-discovery" and "Target Discovery Candidates" not in names:
        # Insert Target Discovery Candidates after Evidence and Current State
        idx = names.index("Evidence and Current State") + 1 if "Evidence and Current State" in names else 2
        names.insert(idx, "Target Discovery Candidates")
    return names


def _normalized_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").splitlines()


def receipt_lines(text: str) -> list[tuple[int, str]]:
    res = []
    in_code_fence = False
    for line_number, line in enumerate(_normalized_lines(text), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if not in_code_fence and VALIDATION_PREFIX_RE.match(line):
            res.append((line_number, stripped))
    return res


def canonical_assessment_body(text: str) -> str:
    """Return LF-normalized assessment content with every validation receipt removed (ignoring code fences)."""
    lines = []
    in_code_fence = False
    for line in _normalized_lines(text):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            lines.append(line)
            continue
        if not in_code_fence and VALIDATION_PREFIX_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines).rstrip("\n") + "\n"


def assessment_digest(text: str) -> str:
    return hashlib.sha256(canonical_assessment_body(text).encode("utf-8")).hexdigest()


def validate_receipt(text: str, *, required: bool, expected_level_or_mode: str | None = None) -> list[Diagnostic]:
    found = receipt_lines(text)
    if not found:
        return [Diagnostic("finalization.receipt.missing", "Finalized assessment requires one validation receipt")] if required else []
    if len(found) > 1:
        return [Diagnostic("finalization.receipt.duplicate", "Assessment contains multiple validation receipts", found[1][0])]
    line_number, line = found[0]
    match = VALIDATION_RECEIPT_RE.fullmatch(line)
    if match is None:
        return [Diagnostic("finalization.receipt.malformed", "Validation receipt must use v2 SHA-256 format: <!-- assessment-validation: 2; level: L2; sha256: ... --> or mode: discovery-only", line_number)]
    
    expected = assessment_digest(text)
    if match.group("digest") != expected:
        return [Diagnostic("finalization.receipt.stale", "Validation receipt SHA-256 does not match canonical assessment body", line_number)]
    
    if expected_level_or_mode:
        rcpt_level = match.group("level")
        rcpt_mode = match.group("mode")
        if expected_level_or_mode == "discovery-only":
            if rcpt_mode != "discovery-only":
                return [Diagnostic("finalization.receipt.mode_mismatch", f"Receipt declares level {rcpt_level} but assessment mode is discovery-only", line_number)]
        elif rcpt_level != expected_level_or_mode:
            return [Diagnostic("finalization.receipt.level_mismatch", f"Receipt declares level {rcpt_level} but expected level is {expected_level_or_mode}", line_number)]
            
    return []


def finalize_assessment_text(text: str, level: str, mode: str = "targeted") -> str:
    body = canonical_assessment_body(text)
    lines = body.rstrip("\n").splitlines()
    digest = assessment_digest(body)
    if mode == "discovery-only" or level == "discovery-only":
        receipt = f"<!-- assessment-validation: 2; mode: discovery-only; sha256: {digest} -->"
        target_marker = marker("L0", mode="discovery-only")
    else:
        receipt = f"<!-- assessment-validation: 2; level: {level}; sha256: {digest} -->"
        target_marker = marker(level, mode=mode)

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

    if mode == "discovery-only" or level == "discovery-only":
        lines = [
            "# Assessment: Architectural Discovery and Triage",
            marker("L0", mode="discovery-only"),
            "",
            "## Decision Summary",
            "- Invocation mode: discovery-only",
            "- Selected target: none",
            "- Selected level: discovery-only",
            "- Recommended design: Refuse autonomous target selection. Hand off repository-wide triage to codebase-issue-auditor.",
            "- Why minimum sufficient: Multiple unrelated candidate concerns rank similarly or require unavailable product intent.",
            "- Protected behavior and contracts: C-1 preserved",
            "- Primary structural pressure: P-1",
            "- Residual risk: none",
            "- Next owner: codebase-issue-auditor",
            "",
            "## Scope and Protected Contracts",
            "- C-1: status: preserved | contract: Replace with API, schema, event, or operational promise | authorization: none",
            "- H-1: status: assessment-only | next: codebase-issue-auditor",
            "",
            "## Evidence and Current State",
            "- F-1: `src/system.py:1` | anchor: `current` | observation: Verified current behavior | source: code | strength: direct | freshness: current",
            "",
            "## Target Discovery Candidates",
            "- T-1: target: `src/module_a.py` | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: medium | likely-level: L1 | blast-radius: local | product-intent-required: false | rank: 1 | status: deferred | reason: Requires product intent alignment before structural change.",
            "- T-2: target: `src/module_b.py` | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: low | likely-level: L1 | blast-radius: local | product-intent-required: true | rank: 2 | status: rejected | reason: Product intent required.",
            "",
            "## Verification and Residual Risk",
            "- V-1: proves: T-1 | method: Inspect candidate evidence | expected: Confirms candidate bounds.",
        ]
        return "\n".join(lines).rstrip() + "\n"

    if level not in contract["levels"]:
        raise ValueError(f"unsupported level: {level}")

    lines = [
        "# Replace With a Concrete Design Decision",
        marker(level, mode=mode),
        "",
        "## Decision Summary",
        f"- Invocation mode: {mode}",
        "- Selected target: Replace with named module, subsystem, boundary, or candidate",
        f"- Selected level: {level}",
        "- Recommended design: Replace with concise summary of the minimum sufficient design",
        "- Why minimum sufficient: Replace with explanation of why lower level fails and higher level is unnecessary",
        "- Protected behavior and contracts: C-1 preserved",
        "- Primary structural pressure: P-1",
        "- Next owner: plan-with-senior-dev",
        "",
        "## Scope and Protected Contracts",
        "- C-1: status: preserved | contract: Replace with API, schema, event, or operational promise | authorization: none",
        "- H-1: status: assessment-only | next: finish assessment, plan-with-senior-dev, codebase-issue-auditor, optimize-codebase-with-senior-dev, or implement-with-senior-dev",
        "",
        "## Evidence and Current State",
        "- F-1: `path:1` | anchor: `existing_anchor` | observation: Replace with verified current behavior | source: code | strength: direct | freshness: current",
        "- Current flow: Replace with input -> owner -> dependency -> side effect -> observable outcome.",
    ]

    if mode == "autonomous-discovery":
        lines.extend([
            "",
            "## Target Discovery Candidates",
            f"- T-1: target: Replace module/boundary | evidence: F-1 | pressure: P-1 | affected: C-1 | confidence: high | likely-level: {level} | blast-radius: local | product-intent-required: false | rank: 1 | status: selected | reason: Dominant candidate with strong repository evidence.",
        ])

    lines.extend([
        "",
        "## Design Pressures and Classification",
        "- P-1: rank: 1 | evidence: F-1 | pressure: Replace with structural cause and observed cost.",
        f"- D-1: level: {level} | selected: minimum safe design | because: F-1, P-1 | rejected: a stronger design adds cost.",
        "",
        "## Alternatives and Pattern Decisions",
        "- O-1: level: L0 | selected: " + ("yes" if level == "L0" else "no") + " | concepts: none | argument-for: Replace | argument-against: Replace | revisit: Replace",
        "- O-2: level: L1 | selected: " + ("yes" if level == "L1" else "no") + " | concepts: Replace | argument-for: Replace | argument-against: Replace | revisit: Replace",
    ])

    if contract["levels"][level]["minimum_alternatives"] >= 3:
        lines.append("- O-3: level: L2 | selected: " + ("yes" if level in ("L2", "L3") else "no") + " | concepts: Replace | argument-for: Replace | argument-against: Replace | revisit: Replace")
    if level == "L3":
        lines.append("- O-4: level: L3 | selected: yes | concepts: Replace | argument-for: Replace | argument-against: Replace | revisit: Replace")

    if contract["levels"][level]["requires_pattern_gate"]:
        lines.extend([
            "",
            "### G-1: Replace Pattern — admit",
            "- Scope: introduced | Result: admit | Evidence: F-1, P-1",
            "",
            "| Gate | Answer | Evidence | Consequence |",
            "|---|---|---|---|",
            "| Q1 | yes | F-1, P-1 | Resolves current pressure |",
            "| Q2 | yes | F-1, P-1 | Evidenced recurrence |",
            "| Q3 | yes | F-1, P-1 | Lower levels insufficient |",
            "| Q4 | yes | F-1, P-1 | Single owner |",
            "| Q5 | yes | F-1, P-1 | Stable contract |",
            "| Q6 | yes | F-1, P-1 | Reduces propagation |",
            "| Q7 | yes | F-1, P-1 | Constrains coupling |",
            "| Q8 | yes | F-1, P-1 | Unambiguous state |",
            "| Q9 | yes | F-1, P-1 | Contracts preserved |",
            "| Q10 | yes | F-1, P-1 | Observable proof |",
            "| Q11 | yes | F-1, P-1 | Operational semantics explicit |",
            "| Q12 | yes | F-1, P-1 | Repository idiom |",
            "| Q13 | yes | F-1, P-1 | Reversible slices |",
            "| Q14 | yes | F-1, P-1 | Net value positive |",
        ])

    lines.extend([
        "",
        "## Verification and Residual Risk",
        "- V-1: proves: D-1 | method: Replace with exact command or test | expected: Replace with observable result.",
    ])

    if level == "L1":
        lines.extend([
            "",
            "## Local Simplification and Preservation",
            "- Responsibility: Replace with cohesive local owner.",
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
        lines.extend(f"- {field.title()}: not-applicable: Replace with concrete reason." for field in contract["operational_fields"])

    if level == "L3":
        lines.extend(["", "## System Ownership and Evolution"])
        lines.extend(f"- {field.title()}: Replace." for field in contract["l3_evolution_fields"])

    return "\n".join(lines).rstrip() + "\n"
