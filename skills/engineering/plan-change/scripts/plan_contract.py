"""Render strict v5 scaffolds from generated canonical contract data."""

from __future__ import annotations

import json
from typing import Any

from plan_contract_data import CONTRACT
from plan_runtime import BLUEPRINT_CONCEPTS, DOMAIN_ATTACKS, OBLIGATIONS, RISK_DOMAINS, SECTIONS, TIERS

INTENTS = tuple(str(value) for value in CONTRACT["intents"])
GENERIC_ATTACKS = tuple(str(value) for value in CONTRACT["required_attacks"])


def load_contract() -> dict[str, Any]:
    """Return generated canonical data without reading repository JSON at runtime."""
    return CONTRACT


def section_names(_: str) -> list[str]:
    return list(SECTIONS)


def _domain_blueprint(domain: str) -> list[str]:
    concepts = " -> ".join(group[0] for group in BLUEPRINT_CONCEPTS[domain])
    return [
        f"### Execution Blueprint: CH-1 — {domain} flow [type: pseudocode; domains: {domain}]",
        "```pseudocode",
        concepts,
        "```",
    ]


def render_scaffold(
    tier: str,
    intent: str,
    domains: list[str] | None = None,
    tier_signals: list[str] | None = None,
) -> str:
    domains = domains or []
    tier_signals = tier_signals or []
    if tier not in TIERS or intent not in INTENTS or len(domains) != len(set(domains)) or not set(domains) <= RISK_DOMAINS:
        raise ValueError("unsupported plan classification")
    if tier != "high-risk" and domains:
        raise ValueError("risk domains require high-risk tier")
    if tier == "high-risk" and not domains:
        raise ValueError("high-risk scaffolds require at least one risk domain")
    allowed_signals = set(CONTRACT["tier_signals"])
    if len(tier_signals) != len(set(tier_signals)) or not set(tier_signals) <= allowed_signals:
        raise ValueError("unsupported tier signal")
    metadata = {
        "provisional": {"intent": intent, "risk_domains": domains, "tier": tier, "tier_signals": tier_signals},
        "final": {"intent": intent, "risk_domains": domains, "tier": tier, "tier_signals": tier_signals},
    }
    obligation_rows = [(domain, obligation) for domain in domains for obligation in OBLIGATIONS[domain]]
    grouped_tests: list[tuple[str, list[str], str]] = []
    obligation_tests: dict[tuple[str, str], str] = {}
    for domain in domains:
        for obligations in CONTRACT["obligation_test_groups"][domain]:
            test_id = f"T-{len(grouped_tests) + 2}"
            grouped_tests.append((domain, obligations, test_id))
            for obligation in obligations:
                obligation_tests[(domain, obligation)] = test_id
    tests = ["T-1", *(test_id for _domain, _obligations, test_id in grouped_tests)]
    rows = [
        "# Replace With an Action-Oriented Outcome",
        "<!-- plan-contract: 5 -->",
        "<!-- plan-metadata: " + json.dumps(metadata, separators=(",", ":")) + " -->",
        "",
        "## Outcome and Scope",
        "- SC-1: given: exact current input or state | when: named entry point receives the trigger | then: exact observable output effect or error | unchanged: named adjacent behavior remains unchanged",
        "",
        "## Evidence Ledger",
        "- F-1: kind: function-signature | path: REPLACE_CURRENT_PATH | lines: REPLACE_CURRENT_RANGE | anchor: REPLACE_CURRENT_ANCHOR | excerpt-sha256: REPLACE_CURRENT_HASH | file-sha256: REPLACE_CURRENT_FILE_HASH | observation: describe current branches errors calls and side effects | parameters: REPLACE_EXACT_SIGNATURE | returns: REPLACE_EXACT_RETURN | async: false",
        "",
        "## Decisions",
        "- D-1: selected: name the exact repository-local behavior and ordering | evidence: F-1 | rejected: name the nearest viable repository-local alternative | drawback: state its concrete caller contract test or rollout cost",
    ]
    if tier != "tiny":
        rows.append("- C-1: constraint: preserve declared behavior | evidence: F-1")
    rows.extend(
        [
            "",
            "## Implementation Specification",
            "- CH-1: path: REPLACE_CURRENT_PATH | anchor: REPLACE_CURRENT_ANCHOR | status: existing | locality: local-production | reversibility: reversible | evidence: F-1 | change: specify propagation consumer caller boundary input literal implementation branches ordering side effects and exact behavior; do not defer any material behavior",
        ]
    )
    if tier == "standard":
        rows.extend(
            [
                "",
                "### Execution Blueprint: CH-1 — hardest flow [type: pseudocode; domains: none]",
                "```pseudocode",
                "read exact input -> validate named condition -> select named branch -> perform ordered effect -> return exact result",
                "```",
            ]
        )
    for domain in domains:
        rows.extend(["", *_domain_blueprint(domain)])
    rows.extend(
        [
            "",
            "## Propagation Record",
            "- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: changed",
            "",
            "## Boundary Traces",
            "- B-1: class: named external or shared boundary | path: F-1 | flow: caller input -> named current anchor -> observable result",
            "",
            "## Domain Obligations",
        ]
    )
    for number, (domain, obligation) in enumerate(obligation_rows, 1):
        alias = CONTRACT["obligation_aliases"][obligation][0]
        test_id = obligation_tests[(domain, obligation)]
        rows.append(
            f"- O-{number}: domain: {domain} | obligation: {obligation} | status: satisfied | "
            f"coverage: {alias} behavior is owned by CH-1 and verified by {test_id} | "
            f"evidence: F-1 | decision: D-1 | changes: CH-1 | tests: {test_id}"
        )
    rows.extend(
        [
            "",
            "## Traceability",
            "| Criterion / constraint | Changes | Tests |",
            "|---|---|---|",
            f"| SC-1 | CH-1 | {', '.join(tests)} |",
        ]
    )
    if tier != "tiny":
        rows.append(f"| C-1 | CH-1 | {', '.join(tests)} |")
    command = "python -m pytest" if tier == "tiny" else "python -m pytest tests/REPLACE_TARGETED_TEST.py"
    rows.extend(
        [
            "",
            "## Verification",
            f"- T-1: given: exact setup input and dependency state | when: named entry point runs | then: exact propagation consumer caller boundary input literal implementation branch ordering side effect output error persisted state or external-call expectation | command: {command}",
        ]
    )
    for domain, obligations, test_id in grouped_tests:
        concepts = ", ".join(CONTRACT["obligation_aliases"][obligation][0] for obligation in obligations)
        attacks = ", ".join(
            alias
            for attack in DOMAIN_ATTACKS.get(domain, ())
            for alias in CONTRACT["attack_aliases"][attack][:1]
        )
        rows.append(
            f"- {test_id}: given: {domain} boundary with exact {concepts} preconditions | "
            f"when: named related obligation paths run | then: exact {concepts} outcomes and {attacks} attack behavior are verified | "
            f"command: python -m pytest tests/REPLACE_{domain}.py"
        )
    rows.extend(["", "## Risks, Assumptions, and Attack"])
    for attack in GENERIC_ATTACKS:
        rows.append(
            f"- A-{attack}: status: repaired | finding: describe the concrete {attack} failure mode and affected boundary | evidence: F-1 | resolution: CH-1, T-1"
        )
    emitted_attacks: set[str] = set()
    for domain in domains:
        domain_test = obligation_tests[(domain, OBLIGATIONS[domain][0])]
        for attack in sorted(DOMAIN_ATTACKS.get(domain, ())):
            if attack in emitted_attacks:
                continue
            emitted_attacks.add(attack)
            rows.append(
                f"- A-{attack}: status: repaired | finding: describe the concrete {domain} {attack} failure mode and exact outcome | evidence: F-1 | resolution: CH-1, {domain_test}"
            )
    if tier == "high-risk":
        rows.append("- R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: named concrete risk")
    return "\n".join(rows) + "\n"
