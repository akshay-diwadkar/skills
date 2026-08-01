# Design Protocol

Complete the seven gates in order. Keep working notes internal; `handoff.md` is
the sole primary artifact.

**Shared vocabulary**

| Term | Meaning |
|---|---|
| Owner | Repository area responsible for a decision and its invariants. |
| Boundary | Point where responsibility or representation changes. |
| Contract | Caller-visible inputs, outputs, errors, and semantics that must remain stable. |
| Depth | Useful behavior hidden relative to exposed interface. |
| Volatility | Likelihood that a detail changes independently of its callers. |
| Propagation | Number and distance of places one change forces to change. |
| Locality | Degree to which related behavior and reasoning stay in one cohesive area. |
| Deletion test | Remove an abstraction; keep it only if deletion duplicates policy, leaks detail, or destroys a real seam. |
| Second-use test | Generalize only when a distinct, evidenced repository use can consume the same contract without special branches. |
| Coupling direction | Direction in which dependency knowledge crosses a boundary. |

Use only the terms that sharpen the current decision. Do not score them or turn
them into a checklist.

## 1. Frame the pressure

Restate the problem for a reader with no assessment context. Bound the behavior
and owner under design without expanding into repository-wide triage. Name
propagation or poor locality only when it creates the pressure. Complete when
current evidence supports the pressure and exclusions.

## 2. Build the evidence ledger

Record only evidence that supports a design claim. Use the ledger syntax in
`handoff-template.md`, cite locations precisely, and distinguish repository,
request, runtime, and external evidence. Local evidence may include an exact
line-range SHA-256; sealing computes it when omitted.
Complete when every material design claim cites a defined `[E-n]` record and
structural conclusions cite repository evidence.

## 3. Compare structural choices

Describe the current structure, chosen structure, and at least one genuinely
distinct alternative. Give each a boundary, owner, core abstraction, and
coupling direction. Reject parameter-only alternatives. Complete when one
alternative changes the core abstraction and the boundary, owner, or coupling
direction, and cites distinct evidence.

## 4. Choose design depth

Choose the best functionality-to-interface ratio: hide volatile or coupled
detail while exposing only caller-controlled behavior. Evaluate consolidation
when shallow pieces change together. Apply the deletion test to wrappers and
the second-use test before generalizing; do not force either test when the
decision does not concern an abstraction. Complete when the depth, exposed
surface, hidden volatility, and rejection rationale are evidence-backed.

## 5. Define the caller contract

Compare current and proposed shared signatures, defaults, nullability, and
caller-visible errors and semantics. State whether the error surface will
shrink, remain flat, or grow, and justify growth. Complete when a caller can
understand the contract without an implementation plan.

## 6. Complete and seal the handoff

Fill all eight sections from `handoff-template.md`. State use-pattern coverage,
what a third pattern changes, consolidation, caller documentation, and
planner-owned questions. Use explicit conclusions instead of placeholders.

Run the single seal command:

```bash
python scripts/seal_assessment.py --repo-root /absolute/repo \
  --output-dir /absolute/output --format json /absolute/draft.md
```

Complete only when it exits successfully and returns canonical diagnostics on
failure or exactly one `handoff.md` on success.

## 7. Seal one handoff

The seal command performs structural validation, local evidence verification,
missing-hash backfill, and the atomic artifact write in one pass. Do not run a
separate validate, finalize, or verify command.

Complete only when the sealer emits exactly one `handoff.md` and every local
evidence binding verifies. Never edit the validated draft or finalized artifact.
