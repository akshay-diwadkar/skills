# Design Protocol

Complete the seven gates in order. Keep working notes internal; `handoff.md` is
the sole primary artifact.

## 1. Frame the pressure

Restate the problem for a reader with no assessment context. Bound the behavior
and ownership under design without expanding into repository-wide triage.
Complete when current evidence supports the pressure and exclusions.

## 2. Build the evidence ledger

Record only evidence that supports a design claim. Use the ledger syntax in
`handoff-template.md`, cite locations precisely, and distinguish repository,
request, runtime, and external evidence. Local evidence may include an exact
line-range SHA-256; finalization computes it when omitted.
Complete when every material design claim cites a defined `[E-n]` record.

## 3. Compare structural choices

Describe the current structure, chosen structure, and at least one genuinely
distinct alternative. Give each a boundary, owner, and core abstraction. Reject
parameter-only alternatives. Complete when one alternative changes the core
abstraction and boundary or ownership, and cites distinct evidence.

## 4. Choose design depth

Choose the best functionality-to-interface ratio: hide volatile or coupled
detail while exposing only caller-controlled behavior. Evaluate consolidation
when shallow pieces change together. Complete when the choice, exposed surface,
hidden detail, and rejection rationale are evidence-backed.

## 5. Define the caller contract

Compare current and proposed shared signatures, defaults, nullability, and
caller-visible errors. State whether the error surface will shrink, remain flat,
or grow, and justify growth. Complete when a caller can understand the contract
without an implementation plan.

## 6. Complete and validate the handoff

Fill all eight sections from `handoff-template.md`. State use-pattern coverage,
what a third pattern changes, consolidation, caller documentation, and
planner-owned questions. Use explicit conclusions instead of placeholders.

Run `scripts/check_assessment.py --repo-root /absolute/repo /absolute/draft.md`.
Complete only when it exits successfully.

## 7. Finalize one handoff

Run `scripts/finalize_assessment.py --repo-root /absolute/repo --output-dir
/absolute/output /absolute/draft.md`, then verify with
`scripts/check_assessment.py --repo-root /absolute/repo --verify-evidence
/absolute/output/handoff.md`.

Complete only when the finalizer emits exactly one `handoff.md` and every local
evidence binding verifies. Never edit the validated draft or finalized artifact.
