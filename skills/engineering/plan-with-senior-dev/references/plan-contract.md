# Plan Contract v3

The executable source of truth is `plan-contract.json`. Generate drafts with `scripts/scaffold_plan.py`; submit plans only through `scripts/finalize_plan.py`.

## Document Shape

Every plan starts with an action-oriented H1, `<!-- plan-contract: 3 -->`, and an explicit tier/task marker. It then uses the generated H2 headings in order. High-Risk plans additionally require Compatibility and Rollout plus Durable Rollback.

Canonical `SC/F/D/CH/T/C/R/A` records remain outside fenced blocks. Define each ID once. Every success criterion and constraint maps to defined changes and tests; every change and test appears in Traceability.

## Execution Blueprints

Standard and High-Risk plans require at least one H3 inside Implementation Specification:

`### Execution Blueprint: CH-1, CH-2 — purpose`

Every referenced change must exist. The H3 body must contain a non-empty fenced block or Markdown table. Fenced content is explanatory and cannot define ledger IDs or citations.

Use pseudocode for control flow, Mermaid for relationships or lifecycle, full typed shapes for interfaces, and tables for compatibility or state behavior. The aid must agree with its `CH-n`, constraints, risks, and test expectations.

## Grounding and Risk

Every `F-n` cites an existing repository-relative `path:line` and an anchor present on that line. Every existing `CH-n` anchor has a matching grounded fact. New anchors use `status: new`.

P0/P1 risks require owning `CH-n` and `T-n` records. High-Risk plans specify mixed-version behavior, rollout order, observability, stop conditions, and durable recovery across every applicable state surface.

## Finalization Receipt

The finalizer canonicalizes line endings to LF, removes an existing single receipt, validates the complete draft, hashes the UTF-8 body without a receipt, and inserts:

`<!-- plan-validation: 3; sha256: <64 lowercase hexadecimal characters> -->`

The receipt appears immediately after the tier/task marker. `check_plan.py --require-finalized` rejects missing, malformed, duplicated, or stale receipts. A receipt is an integrity signal against accidental validation omission, not a security boundary against a malicious local actor.

Contract v1 and v2 are unsupported and must fail rather than enter a compatibility adapter.
