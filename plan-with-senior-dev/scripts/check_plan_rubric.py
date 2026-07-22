#!/usr/bin/env python3
"""Check v3 plan fields for decision-complete content."""

from __future__ import annotations

import argparse
import re

from _plan_utils import Diagnostic, read_plan, strip_fenced_code_blocks
from plan_contract import load_contract
from plan_model import CHANGE_RE, FACT_RE, definitions, parse_markdown


DECISION_RE = re.compile(
    r"^- D-[1-9]\d*:\s+selected:\s+.+\|\s+because:\s+.+\|\s+rejected:\s+.+$",
    re.MULTILINE | re.IGNORECASE,
)
TEST_RE = re.compile(
    r"^- T-[1-9]\d*:\s+given:\s+.+\|\s+expect:\s+.+\|\s+command:\s+`[^`]+`$",
    re.MULTILINE | re.IGNORECASE,
)
CONSTRAINT_RE = re.compile(
    r"^- C-[1-9]\d*:\s+.+\|\s+status:\s+(?:preserved|modified|at-risk)$",
    re.MULTILINE | re.IGNORECASE,
)
RISK_RE = re.compile(
    r"^- R-[1-9]\d*\s+P[012]:\s+.+\|\s+Resolution:\s+.+$",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=tuple(load_contract()["tiers"]), required=True)
    parser.add_argument("path", nargs="?")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--warn", action="store_true")
    return parser.parse_args()


def _section_body(text: str, name: str) -> str:
    section = parse_markdown(text).find_section(name)
    return section.body if section else ""


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def validate(text: str, tier: str) -> list[Diagnostic]:
    contract = load_contract()
    diagnostics: list[Diagnostic] = []
    outcome = _section_body(text, "Outcome and Scope")
    evidence = strip_fenced_code_blocks(_section_body(text, "Evidence Ledger"))
    decisions = strip_fenced_code_blocks(_section_body(text, "Decisions"))
    implementation = strip_fenced_code_blocks(_section_body(text, "Implementation Specification"))
    verification = strip_fenced_code_blocks(_section_body(text, "Verification"))
    risks = strip_fenced_code_blocks(_section_body(text, "Risks, Assumptions, and Attack"))

    if not re.search(r"\bIn scope:\s+\S", outcome, re.IGNORECASE) or not re.search(r"\bUnchanged:\s+\S", outcome, re.IGNORECASE):
        diagnostics.append(Diagnostic("rubric.scope.boundaries", "Outcome and Scope must define In scope and Unchanged boundaries"))
    if len(FACT_RE.findall(evidence)) != len(definitions(evidence, "F")):
        diagnostics.append(Diagnostic("rubric.fact.format", "Every F-n must use the canonical citation, anchor, and observation format"))
    if len(DECISION_RE.findall(decisions)) != len(definitions(decisions, "D")):
        diagnostics.append(Diagnostic("rubric.decision.format", "Every D-n must state selected, because, and rejected fields"))
    if len(CHANGE_RE.findall(implementation)) != len(definitions(implementation, "CH")):
        diagnostics.append(Diagnostic("rubric.change.format", "Every CH-n must state path, anchor, status, and exact change"))
    if len(TEST_RE.findall(verification)) != len(definitions(verification, "T")):
        diagnostics.append(Diagnostic("rubric.test.format", "Every T-n must state exact given, expect, and command fields"))

    prose = strip_fenced_code_blocks(text)
    if tier in {"standard", "high-risk"} and len(CONSTRAINT_RE.findall(prose)) != len(definitions(prose, "C")):
        diagnostics.append(Diagnostic("rubric.constraint.format", "Every C-n must classify its status"))
    if tier == "high-risk" and len(RISK_RE.findall(risks)) != len(definitions(risks, "R")):
        diagnostics.append(Diagnostic("rubric.risk.format", "Every R-n must state severity, scenario, consequence, and Resolution"))

    required_attacks = contract["tiers"][tier]["required_attacks"]
    for attack in required_attacks:
        pattern = rf"^- {attack}:\s+(?:repaired|dismissed|not-applicable)\s+\|\s+evidence:\s+.+$"
        if not re.search(pattern, risks, re.MULTILINE | re.IGNORECASE):
            diagnostics.append(Diagnostic("rubric.attack.missing", f"{attack} must be recorded as repaired, dismissed, or not-applicable with evidence"))
    if not re.search(r"^- Assumptions:\s+(?:None\b.*|.+(?:low-impact|reversible).*)$", risks, re.MULTILINE | re.IGNORECASE):
        diagnostics.append(Diagnostic("rubric.assumptions.unclassified", "Assumptions must be None or explicitly low-impact and reversible"))

    if tier == "high-risk":
        compatibility = _section_body(text, "Compatibility and Rollout")
        rollback = _section_body(text, "Durable Rollback")
        compatibility_concepts = (
            _has_any(compatibility, (r"\bold\b", r"\blegacy\b", r"\bexisting\b", r"\bprevious\b")),
            _has_any(compatibility, (r"\bnew\b", r"\btarget\b", r"\bupdated\b")),
            _has_any(compatibility, (r"\border\b", r"\bbefore\b", r"\bfirst\b", r"\bsequence\b")),
            _has_any(compatibility, (r"\bmonitor", r"\bobserv", r"\bmetric", r"\btelemetry\b")),
            _has_any(compatibility, (r"\bstop\b", r"\bhalt\b", r"\babort\b", r"\bpause\b", r"\bdisable\b")),
        )
        if not all(compatibility_concepts):
            diagnostics.append(Diagnostic("rubric.compatibility.incomplete", "Compatibility and Rollout must cover old/new behavior, order, monitoring, and stop conditions"))
        if not re.search(r"\b(code|data|queue|cache|external|irreversible)\b", rollback, re.IGNORECASE):
            diagnostics.append(Diagnostic("rubric.rollback.incomplete", "Durable Rollback must cover durable state or explicitly eliminate each applicable surface"))
    return diagnostics


def main() -> int:
    args = parse_args()
    diagnostics = validate(read_plan(args.path), args.tier)
    if diagnostics:
        print("Plan rubric check findings:")
        for item in diagnostics:
            print(f"- {item}")
    else:
        print("Plan rubric check passed.")
    errors = [item for item in diagnostics if not item.is_warning]
    warnings = [item for item in diagnostics if item.is_warning]
    return 1 if errors or (warnings and not args.warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())
