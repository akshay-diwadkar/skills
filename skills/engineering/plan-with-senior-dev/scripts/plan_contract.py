"""Load and render the canonical v3 plan contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "plan-contract.json"


def load_contract() -> dict[str, Any]:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("contract_version") != 3:
        raise ValueError("plan contract must have contract_version 3")
    return data


def section_names(tier: str) -> list[str]:
    contract = load_contract()
    tier_contract = contract["tiers"][tier]
    return [*contract["base_sections"], *tier_contract["extra_sections"]]


def render_scaffold(tier: str, task_type: str) -> str:
    contract = load_contract()
    if tier not in contract["tiers"]:
        raise ValueError(f"unsupported tier: {tier}")
    if task_type not in contract["task_types"]:
        raise ValueError(f"unsupported task type: {task_type}")

    tier_contract = contract["tiers"][tier]
    required_attacks = contract["tiers"][tier]["required_attacks"]
    lines: list[str] = [
        "# Replace With an Action-Oriented Outcome",
        contract["marker"],
        f"<!-- tier: {tier}; task-type: {task_type} -->",
        "",
        "## Outcome and Scope",
        "- SC-1: Replace with one measurable observable result.",
        "- In scope: Replace with exact behavior and surfaces.",
        "- Unchanged: Replace with explicit invariants and exclusions.",
        "",
        "## Evidence Ledger",
        "- F-1: `path:1` | anchor: `existing_anchor` | observation: Replace with verified current behavior.",
        "",
        "## Decisions",
        "- D-1: selected: Replace with exact approach | because: Replace with cited constraint or precedent | rejected: Replace with nearest alternative and drawback.",
        "",
        "## Implementation Specification",
        "- CH-1: `path` | anchor: `existing_symbol` | status: existing | change: Replace with exact behavior, branches, errors, and side effects.",
    ]
    if tier_contract["blueprint_required"]:
        lines.extend([
            "",
            "### Execution Blueprint: CH-1 — Replace with the hardest implementation flow",
            "```pseudocode",
            "Replace with exact branches, errors, ordering, and side effects.",
            "```",
        ])
    lines.extend([
        "",
        "## Traceability",
        "| Criterion / constraint | Changes | Tests | Status / rollback |",
        "|---|---|---|---|",
        "| SC-1 | CH-1 | T-1 | Replace with preserved, modified, or rollback behavior |",
        "",
        "## Verification",
        "- T-1: given: Replace with exact input and state | expect: Replace with exact output, error, or side effect | command: `replace-with-command`",
        "",
        "## Risks, Assumptions, and Attack",
        "- Assumptions: None, or list only low-impact reversible assumptions.",
    ])
    lines.extend(
        f"- {attack}: not-applicable | evidence: Replace with concrete cited reason."
        for attack in required_attacks
    )
    if tier in {"standard", "high-risk"}:
        lines.insert(lines.index("## Traceability") + 1, "- C-1: Replace with an at-risk or preserved constraint | status: preserved")
    if tier == "high-risk":
        lines.extend([
            "- R-1 P1: Replace with concrete scenario and consequence | Resolution: CH-1/T-1",
            "",
            "## Compatibility and Rollout",
            "Replace with old/new reader, writer, client, deployment-order, monitoring, and stop behavior.",
            "",
            "## Durable Rollback",
            "Replace with code, data, queued-work, cache, and irreversible-effect recovery.",
        ])
    return "\n".join(lines).rstrip() + "\n"
