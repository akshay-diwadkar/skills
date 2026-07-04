# Pre-Mortem Protocol

Use this before finalizing Standard or High-risk plans, and whenever a plan feels optimistic. Imagine the implementation already failed, then identify concrete causes from repo evidence.

The goal is to fix plan-breaking blind spots, not to add a long risk appendix.

## Finding Requirements

Every finding must include:

- Evidence from code, tests, docs, config, schemas, migrations, or an explicit assumption.
- Consequence if the risk happens.
- Action the plan will take.
- Tier: P0, P1, or P2.
- Owner section: the plan section that must change or carry the mitigation.

Risk tiers:

- P0: blocks finalization. Resolve the plan or ask the user before finalizing.
- P1: must be addressed in the plan.
- P2: acceptable to record as an assumption or note.

Finding shape:

```text
Scope - P1: The plan treats [X] as full scope, but [Y] also depends on it because [evidence]. Consequence: [impact]. Action: [plan change]. Owner section: [section].
```

## Categories

### Scope Blast Radius

Ask: who imports, calls, subscribes to, renders, schedules, or configures the changed behavior? Do shared helpers, generated clients, base classes, jobs, webhooks, or events widen the blast radius?

### Persisted Data and Compatibility

Ask: does the plan change stored shape, enum values, serialization, migrations, public contracts, cache entries, browser storage, or queued messages? Can old and new code read each other's data during rollout?

### Performance and Scale

Ask: does this add nested loops, repeated lookups, unbounded loads, scans, hot-path network calls, queue contention, locks, or rate-limit pressure?

### External Integration Assumptions

Ask: which external behavior is assumed: response shape, auth, idempotency, pagination, rate limits, errors, or availability? Has it been checked against docs, source, contract tests, or local examples?

### Testability Gaps

Ask: can the critical behavior be triggered and asserted through an existing test boundary? Does the plan rely on manual QA for a critical path?

### Rollback Traps

Ask: does the plan write data old code cannot read, delete or rename durable state, publish messages, notify users, charge money, or call external systems irreversibly?

### Domain and Terminology Confusion

Ask: do `CONTEXT.md`, code names, UI labels, docs, and the user mean the same thing? Are synonyms being split or different concepts being collapsed?

## Output by Tier

Tiny:

- Run this mentally.
- Emit only real findings.
- If no material findings exist, add one assumption sentence explaining the specific low-risk reason.

Standard:

- Include P0 and P1 findings in the plan.
- Include only material P2 findings as assumptions.
- Do not list N/A categories.

High-risk:

- Include compact `Pre-Mortem Findings`.
- No unresolved P0 findings may remain.
- P1 findings must map to migration, compatibility, fallback, test, rollout, or rollback steps.

## Sanity Checks

- If a non-trivial plan has no findings, re-check Scope Blast Radius, Testability Gaps, and Rollback Traps.
- If findings are generic, redo them with file paths, data shapes, config names, dependency names, or explicit assumptions.
- If the pre-mortem makes the plan too long, keep the action and remove category narration.
