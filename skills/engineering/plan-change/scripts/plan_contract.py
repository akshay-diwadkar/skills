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
        "## Outcome and Scope", "- SC-1: given: exact current input or state | when: named entry point receives the trigger | then: exact observable output effect or error | unchanged: named adjacent behavior remains unchanged", "",
        "## Evidence Ledger", "- F-1: kind: function-signature | path: REPLACE_CURRENT_PATH | lines: REPLACE_CURRENT_RANGE | anchor: REPLACE_CURRENT_ANCHOR | excerpt-sha256: REPLACE_CURRENT_HASH | file-sha256: REPLACE_CURRENT_FILE_HASH | observation: describe current branches errors calls and side effects | parameters: REPLACE_EXACT_SIGNATURE | returns: REPLACE_EXACT_RETURN", "",
        "## Decisions", "- D-1: selected: name the exact repository-local behavior and ordering | evidence: F-1 | rejected: name the nearest viable repository-local alternative | drawback: state its concrete caller contract test or rollout cost",
    ]
    if tier != "tiny":
        rows.append("- C-1: constraint: preserve declared behavior | evidence: F-1")
    rows.extend(["", "## Implementation Specification", "- CH-1: path: REPLACE_CURRENT_PATH | anchor: REPLACE_CURRENT_ANCHOR | status: existing | evidence: F-1 | change: specify input branches error behavior ordering side effects and caller ownership; do not defer any material behavior"])
    if tier == "standard":
        rows.extend(["", "### Execution Blueprint: CH-1 — hardest flow [type: pseudocode]", "```pseudocode", "validate input -> branch -> effect -> verify", "```"])
    if tier == "standard":
        rows[-2] = "read exact input -> validate named condition -> select named branch -> perform ordered effect -> return or raise exact observable result"
    if tier == "high-risk":
        for domain in domains:
            rows.extend([""] + _domain_blueprint(domain))
    rows.extend(["", "## Propagation Record", "- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: changed", "", "## Boundary Traces", "- B-1: class: named external or shared boundary | path: F-1 | flow: caller input -> named current anchor -> observable result", "", "## Domain Obligations"])
    if tier == "high-risk":
        number = 1
        for domain in domains:
            for obligation in OBLIGATIONS[domain]:
                rows.append(f"- O-{number}: domain: {domain} | obligation: {obligation} | status: satisfied | evidence: F-1 | decision: D-1 | changes: CH-1 | tests: T-{domains.index(domain) + 2}")
                number += 1
    rows.extend(["", "## Traceability", "| Criterion / constraint | Changes | Tests |", "|---|---|---|", f"| SC-1 | CH-1 | {', '.join(tests)} |"])
    if tier != "tiny":
        rows.append(f"| C-1 | CH-1 | {', '.join(tests)} |")
    command = "python -m pytest" if tier == "tiny" else "python -m pytest tests/REPLACE_TARGETED_TEST.py"
    rows.extend(["", "## Verification", f"- T-1: given: exact setup input and dependency state | when: named entry point runs | then: exact output error persisted state or external-call expectation | command: {command}"])
    for index, domain in enumerate(domains, 2):
        rows.append(f"- T-{index}: given: {domain} boundary with exact precondition | when: named failure or mixed-version path runs | then: exact {domain} behavior is verified | command: python -m pytest tests/REPLACE_{domain}.py")
    rows.extend(["", "## Risks, Assumptions, and Attack"])
    for attack in GENERIC_ATTACKS:
        status = "dismissed" if attack == "boundary-input" else "repaired"
        resolution = "F-1" if status == "dismissed" else "CH-1, T-1"
        rows.append(f"- A-{attack}: status: {status} | finding: describe the concrete {attack} failure mode and affected boundary | evidence: F-1 | resolution: {resolution}")
    for domain in domains:
        for attack in sorted(DOMAIN_ATTACKS.get(domain, ())):
            rows.append(f"- A-{attack}: status: repaired | finding: describe the concrete {domain} {attack} failure mode and exact outcome | evidence: F-1 | resolution: CH-1, T-{domains.index(domain) + 2}")
    if tier == "high-risk":
        rows.append("- R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: named concrete risk")
    return "\n".join(rows) + "\n"
