"""Render the strict v5 planning scaffold."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "plan-contract.json"


def load_contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if value.get("contract_version") != 5:
        raise ValueError("plan contract must have contract_version 5")
    return value


def section_names(_: str) -> list[str]:
    return [
        "Outcome and Scope",
        "Evidence Ledger",
        "Decisions",
        "Implementation Specification",
        "Propagation Record",
        "Boundary Traces",
        "Domain Obligations",
        "Traceability",
        "Verification",
        "Risks, Assumptions, and Attack",
    ]


def render_scaffold(tier: str, intent: str, domains: list[str] | None = None) -> str:
    contract, domains = load_contract(), domains or []
    if (
        tier not in contract["tiers"]
        or intent not in contract["intents"]
        or len(domains) != len(set(domains))
        or not set(domains) <= set(contract["risk_domains"])
    ):
        raise ValueError("unsupported plan classification")
    metadata = {
        "provisional": {"intent": intent, "risk_domains": domains, "tier": tier},
        "final": {"intent": intent, "risk_domains": domains, "tier": tier},
    }
    rows = [
        "# Replace With an Action-Oriented Outcome",
        "<!-- plan-contract: 5 -->",
        "<!-- plan-metadata: " + json.dumps(metadata, separators=(",", ":")) + " -->",
        "",
        "## Outcome and Scope",
        "- SC-1: given: exact starting state | when: exact trigger | then: observable result | unchanged: stable behavior",
        "",
        "## Evidence Ledger",
        "- F-1: kind: function-signature | path: src/example.py | lines: 1-1 | anchor: example | excerpt-sha256: REPLACE | file-sha256: REPLACE | observation: planner-authored observation | parameters: REPLACE | returns: REPLACE",
        "",
        "## Decisions",
        "- D-1: selected: exact approach | evidence: F-1 | rejected: nearest alternative | drawback: concrete repository-grounded drawback",
        *(["- C-1: constraint: preserve declared behavior | evidence: F-1"] if tier != "tiny" else []),
        "",
        "## Implementation Specification",
        "- CH-1: path: src/example.py | anchor: example | status: existing | evidence: F-1 | change: exact branches errors ordering and effects",
        *(
            [
                "",
                "### Execution Blueprint: CH-1 — hardest flow [type: pseudocode]",
                "```pseudocode",
                "validate -> branch -> effect -> verify",
                "```",
            ]
            if tier != "tiny"
            else []
        ),
        "",
        "## Propagation Record",
        "- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: changed",
        "",
        "## Boundary Traces",
        "- B-1: class: API request | path: F-1 | flow: request -> change -> result",
        "",
        "## Domain Obligations",
        *(["- O-1: domain: REPLACE | obligation: REPLACE | status: satisfied | evidence: F-1 | decision: D-1 | changes: CH-1 | tests: T-1"] if tier == "high-risk" else []),
        "",
        "## Traceability",
        "| Criterion / constraint | Changes | Tests |",
        "|---|---|---|",
        "| SC-1 | CH-1 | T-1 |",
        "",
        "## Verification",
        "- T-1: given: exact state | when: exact trigger | then: exact result | command: python -m pytest",
        "",
        "## Risks, Assumptions, and Attack",
        "- A-forgotten-propagation: status: repaired | finding: propagation inventory reviewed | evidence: F-1 | resolution: CH-1, T-1",
        "- A-boundary-input: status: dismissed | finding: input boundary is unchanged | evidence: F-1 | resolution: F-1",
        "- A-literal-implementation: status: repaired | finding: implementation follows decision | evidence: F-1 | resolution: CH-1, T-1",
        *(["- R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: named concrete risk"] if tier == "high-risk" else []),
    ]
    if False:  # Blueprint is emitted inside Implementation Specification above.
        rows.extend(
            [
                "",
                "### Execution Blueprint: CH-1 — hardest flow [type: pseudocode]",
                "```pseudocode",
                "validate -> branch -> effect -> verify",
                "```",
            ]
        )
    return "\n".join(rows) + "\n"
