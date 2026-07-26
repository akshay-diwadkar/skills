"""Load and render the canonical v4 plan contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "plan-contract.json"


def load_contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if value.get("contract_version") != 4:
        raise ValueError("plan contract must have contract_version 4")
    return value


def section_names(tier: str) -> list[str]:
    """Expose v4 section order for scaffolding and package checks."""
    contract = load_contract()
    if tier not in contract["tiers"]:
        raise ValueError(f"unsupported tier: {tier}")
    return list(contract["base_sections"])


def render_scaffold(tier: str, intent: str, domains: list[str] | None = None) -> str:
    contract = load_contract()
    domains = domains or []
    if tier not in contract["tiers"] or intent not in contract["intents"]:
        raise ValueError("unsupported plan classification")
    if len(domains) != len(set(domains)) or any(domain not in contract["risk_domains"] for domain in domains):
        raise ValueError("risk domains must be known and unique")
    metadata = {
        "provisional": {"intent": intent, "risk_domains": domains, "tier": tier},
        "final": {"intent": intent, "risk_domains": domains, "tier": tier},
    }
    lines = [
        "# Replace With an Action-Oriented Outcome",
        contract["marker"],
        "<!-- plan-metadata: " + json.dumps(metadata, separators=(",", ":")) + " -->",
        "<!-- plan-repository: Replace with finalizer-generated binding JSON -->",
        "",
        "## Outcome and Scope",
        "- SC-1: given: exact initial state | when: exact trigger | then: observable result | unchanged: stable behavior",
        "- In scope: exact behavior and surfaces.",
        "- Unchanged: explicit invariants and exclusions.",
        "",
        "## Evidence Ledger",
        "- F-1: path: `path` | lines: 1-1 | anchor: `symbol` | excerpt-sha256: `hash` | file-sha256: `hash` | observation: verified current behavior.",
        "",
        "## Decisions",
        "- D-1: selected: exact approach | evidence: F-1 | rejected: nearest alternative | drawback: concrete drawback.",
        "",
        "## Implementation Specification",
        "- CH-1: path: `path` | anchor: `symbol` | status: existing | evidence: F-1 | change: exact behavior, branches, errors, ordering, and side effects.",
        "",
        "## Propagation Record",
        "- P-1: path: `path` | surface: caller or generated surface | disposition: changed | owner: CH-1.",
        "",
        "## Boundary Traces",
        "- B-1: class: API request | path: F-1 | flow: caller -> entry -> side effect -> result.",
        "",
        "## Domain Obligations",
        "- O-none: not-applicable | evidence: F-1.",
        "",
        "## Traceability",
        "| Criterion / constraint | Changes | Tests |",
        "|---|---|---|",
        "| SC-1 | CH-1 | T-1 |",
        "",
        "## Verification",
        "- T-1: given: exact input and state | expect: exact output/error/effect | command: `exact command`.",
        "",
        "## Risks, Assumptions, and Attack",
        "- Assumptions: None.",
        "- A-forgotten-propagation: repaired | evidence: P-1.",
        "- A-boundary-input: repaired | evidence: T-1.",
        "- A-literal-implementation: repaired | evidence: D-1.",
    ]
    if tier != "tiny":
        lines.insert(lines.index("## Traceability"), "- C-1: preserved constraint | status: preserved.")
    if tier == "high-risk":
        lines.insert(lines.index("## Traceability"), "- R-1: P1 | risk: deployment or compatibility failure | owner: CH-1/T-1.")
    if contract["tiers"][tier]["blueprint_required"]:
        lines.extend(
            [
                "",
                "### Execution Blueprint: CH-1 — hardest flow",
                "```pseudocode",
                "exact branches, errors, ordering, and side effects",
                "```",
            ]
        )
    for domain in domains:
        for obligation in contract["domain_obligations"].get(domain, []):
            lines.insert(lines.index("## Traceability"), f"- O-{domain}-{obligation}: required | evidence: F-1.")
        for attack in contract["domain_attacks"].get(domain, []):
            lines.append(f"- A-{attack}: assess applicability | evidence: F-1.")
    return "\n".join(lines) + "\n"
