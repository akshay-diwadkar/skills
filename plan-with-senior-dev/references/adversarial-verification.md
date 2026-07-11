# Adversarial Verification

Run after a complete draft. Attack instructions, not intentions. Repair the owning section for every material finding.

## Attack Sequence

1. Literal execution: follow each step exactly and find missing names, types, ownership, ordering, or behavior.
2. Counterexample: choose empty, zero, null, invalid, legacy, unauthorized, duplicated, and maximum-size inputs.
3. Propagation: search every changed symbol and inspect a caller-of-caller, test double, generated surface, and config/schema surface.
4. Dependency surprise: assume a library or service times out, returns a valid alternate shape, rate-limits, or retries.
5. Ordering: interleave operations, redeploy mixed versions, retry after timeout, and run the operation twice.
6. Partial failure: let step N commit and N+1 fail; inspect data, external state, and replay behavior.
7. Scale: test the planned algorithm and side effects at 10x and 100x expected volume.
8. Rollback: execute rollback after partial rollout and after new-format data or external effects exist.

## Finding Format

```text
R-1 P1 [attack]: Given [specific state/input/order], the draft [exact defect].
Consequence: [observable impact].
Resolution: [exact change to CH-n/T-n/compatibility/migration/rollback].
```

P0 blocks finalization. P1 must modify the plan. P2 may remain only with evidence and explicit acceptance.

Do not manufacture three cosmetic findings. If an attack vector is immaterial, state the exact evidence that eliminates it. One real P1 that repairs the plan is more valuable than three keyword-rich bullets.

## Cross-Consistency Audit

- Compare every success criterion with every stated invariant; reject mutually exclusive requirements.
- Compare pseudocode branches with test expectations; identical preconditions cannot require incompatible results.
- Compare interface shapes with current citations and compatibility claims.
- Compare propagation entries with implementation steps; every “update required: yes” needs an owner.
- Compare at-risk constraints with tests and rollback.
- Compare risks with actions; actions must appear in implementation or verification, not only the risk list.

## Stop Rule

Finalize only when no unresolved P0 exists, every P1 has changed its owning section, every success criterion is traceable, and remaining assumptions are low-impact and reversible.

