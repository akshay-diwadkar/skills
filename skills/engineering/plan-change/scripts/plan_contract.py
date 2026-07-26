"""Render a strict v5 scaffold from the bundled canonical runtime data."""

from __future__ import annotations

import json

from plan_runtime import DOMAIN_ATTACKS, OBLIGATIONS, RISK_DOMAINS, SECTIONS, TIERS

INTENTS = ("feature", "bug-fix", "refactor")
GENERIC_ATTACKS = ("forgotten-propagation", "boundary-input", "literal-implementation")


def load_contract() -> dict[str, object]:
    """Compatibility helper; installed scaffolds never read repository JSON."""
    return {"contract_version": 5, "tiers": TIERS, "intents": INTENTS, "risk_domains": tuple(sorted(RISK_DOMAINS))}


def section_names(_: str) -> list[str]:
    return list(SECTIONS)


def _domain_blueprint(domain: str) -> list[str]:
    concepts = {
        "security": "principal identity -> tenant boundary -> validation order -> authorization owner -> deny behavior",
        "concurrency": "shared state -> lock boundary -> worst interleaving -> duplicate retry idempotency -> reconciliation",
        "public-contract": "current shape -> proposed shape -> old writer new reader -> new writer old reader -> mixed-version rollout",
        "durable-state": "current state -> target state -> partial state -> interrupted state -> rollback and deployment order",
        "migration": "current state -> target state -> partial state -> interrupted state -> rollback and deployment order",
        "external-integration": "authentication -> timeout -> retry classes -> ambiguous success -> reconciliation",
        "irreversible-external-effect": "irreversible boundary -> duplicate prevention -> ambiguous success -> compensation reconciliation",
    }
    return [f"### Execution Blueprint: CH-1 — {domain} flow [type: pseudocode]", "```pseudocode", concepts[domain], "```"]


def render_scaffold(tier: str, intent: str, domains: list[str] | None = None) -> str:
    domains = domains or []
    if tier not in TIERS or intent not in INTENTS or len(domains) != len(set(domains)) or not set(domains) <= RISK_DOMAINS:
        raise ValueError("unsupported plan classification")
    if tier != "high-risk" and domains:
        raise ValueError("risk domains require high-risk tier")
    metadata = {"provisional": {"intent": intent, "risk_domains": domains, "tier": tier}, "final": {"intent": intent, "risk_domains": domains, "tier": tier}}
    tests = ["T-1"] + [f"T-{index}" for index in range(2, len(domains) + 2)]
    rows = [
        "# Replace With an Action-Oriented Outcome", "<!-- plan-contract: 5 -->", "<!-- plan-metadata: " + json.dumps(metadata, separators=(",", ":")) + " -->", "",
        "## Outcome and Scope", "- SC-1: given: exact starting state | when: exact trigger | then: observable result | unchanged: stable behavior", "",
        "## Evidence Ledger", "- F-1: kind: function-signature | path: src/example.py | lines: 1-1 | anchor: example | excerpt-sha256: REPLACE | file-sha256: REPLACE | observation: planner-authored observation | parameters: REPLACE | returns: REPLACE", "",
        "## Decisions", "- D-1: selected: exact approach | evidence: F-1 | rejected: nearest alternative | drawback: concrete repository-grounded drawback",
    ]
    if tier != "tiny":
        rows.append("- C-1: constraint: preserve declared behavior | evidence: F-1")
    rows.extend(["", "## Implementation Specification", "- CH-1: path: src/example.py | anchor: example | status: existing | evidence: F-1 | change: exact branches errors ordering and effects"])
    if tier == "standard":
        rows.extend(["", "### Execution Blueprint: CH-1 — hardest flow [type: pseudocode]", "```pseudocode", "validate input -> branch -> effect -> verify", "```"])
    if tier == "high-risk":
        for domain in domains:
            rows.extend([""] + _domain_blueprint(domain))
    rows.extend(["", "## Propagation Record", "- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: changed", "", "## Boundary Traces", "- B-1: class: API request | path: F-1 | flow: request -> change -> result", "", "## Domain Obligations"])
    if tier == "high-risk":
        number = 1
        for domain in domains:
            for obligation in OBLIGATIONS[domain]:
                rows.append(f"- O-{number}: domain: {domain} | obligation: {obligation} | status: satisfied | evidence: F-1 | decision: D-1 | changes: CH-1 | tests: T-{domains.index(domain) + 2}")
                number += 1
    rows.extend(["", "## Traceability", "| Criterion / constraint | Changes | Tests |", "|---|---|---|", f"| SC-1 | CH-1 | {', '.join(tests)} |"])
    if tier != "tiny":
        rows.append(f"| C-1 | CH-1 | {', '.join(tests)} |")
    rows.extend(["", "## Verification", "- T-1: given: exact state | when: exact trigger | then: exact result | command: python -m pytest"])
    for index, domain in enumerate(domains, 2):
        rows.append(f"- T-{index}: given: {domain} boundary | when: required failure path runs | then: {domain} behavior is verified | command: python -m pytest")
    rows.extend(["", "## Risks, Assumptions, and Attack"])
    for attack in GENERIC_ATTACKS:
        status = "dismissed" if attack == "boundary-input" else "repaired"
        resolution = "F-1" if status == "dismissed" else "CH-1, T-1"
        rows.append(f"- A-{attack}: status: {status} | finding: {attack} behavior is explicitly reviewed | evidence: F-1 | resolution: {resolution}")
    for domain in domains:
        for attack in sorted(DOMAIN_ATTACKS.get(domain, ())):
            rows.append(f"- A-{attack}: status: repaired | finding: {domain} {attack} behavior is explicitly verified | evidence: F-1 | resolution: CH-1, T-{domains.index(domain) + 2}")
    if tier == "high-risk":
        rows.append("- R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: named concrete risk")
    return "\n".join(rows) + "\n"
