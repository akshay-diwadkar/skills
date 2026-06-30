# Pre-Mortem Protocol

Use this before finalizing Standard or High-risk plans, and whenever a plan feels optimistic. Imagine the implementation already failed, then identify the concrete reason from repo evidence.

The goal is not a long risk appendix. The goal is to find plan-breaking blind spots early enough to fix the plan.

## How to Run

For each category, write either a finding or `N/A - [specific reason]`.

Every finding must include:

- Evidence from code, tests, docs, config, schemas, migrations, or an explicit assumption.
- Consequence if the risk happens.
- Action the plan will take.
- Tier: P0, P1, or P2.

Risk tiers:

- P0: blocks finalization. Resolve the plan or ask the user before finalizing.
- P1: must be addressed in the plan.
- P2: acceptable to record as an assumption or note.

## Categories

### Scope Blast Radius

Failure: the plan changed more than the explored surface.

Ask:

- Who imports, calls, subscribes to, or renders the changed behavior?
- Do shared helpers, base classes, generated clients, or config files widen the blast radius?
- Are jobs, webhooks, events, or background workers coupled to this path?

Finding shape:

```text
Scope - [P0/P1/P2]: The plan treats [X] as the full scope, but [Y] also depends on it because [evidence]. Action: [plan change].
```

### Persisted Data and Compatibility

Failure: old persisted data, serialized messages, files, cache entries, or browser storage do not match the new assumptions.

Ask:

- Does the plan change stored shape, enum values, serialization, migrations, or public contracts?
- Can old code read data written by new code, and can new code read old data?
- What happens to in-flight jobs, sessions, or queued messages during rollout?

Finding shape:

```text
Data - [P0/P1/P2]: Existing [data] in [location] has [shape]. The plan assumes [new shape]. Action: [compatibility, migration, or rollback step].
```

### Performance and Scale

Failure: the approach works for small data but degrades on realistic load.

Ask:

- Does this add nested loops, repeated lookups, unbounded loads, database scans, or hot-path network calls?
- Are filter or sort columns indexed?
- Does the plan introduce contention on locks, queues, pools, or rate limits?

Finding shape:

```text
Performance - [P0/P1/P2]: At [scale], [operation] can [degrade] because [evidence]. Action: [limit, index, batch, cache, or test].
```

### External Integration Assumptions

Failure: an external service, library, API, or generated client behaves differently than expected.

Ask:

- Which external behavior is assumed: response shape, auth, idempotency, pagination, rate limits, errors, or availability?
- Has that behavior been checked against docs, source, contract tests, or local examples?
- Is there a fallback for external failure?

Finding shape:

```text
Integration - [P0/P1/P2]: The plan assumes [system] will [behavior], but this is [evidence or assumption]. Action: [verification, fallback, or contract test].
```

### Testability Gaps

Failure: the important behavior cannot be exercised through an existing seam.

Ask:

- What is the most important behavior this plan introduces or changes?
- Can tests trigger it and assert the result through an existing boundary?
- Does the plan rely on manual QA for a critical path?

Finding shape:

```text
Testability - [P0/P1/P2]: [Behavior] is not testable at [level] because [reason]. Action: [test seam, integration test, fixture, or accepted manual check].
```

### Rollback Traps

Failure: reverting code makes the system worse because state, contracts, or external side effects already changed.

Ask:

- Does the plan write data old code cannot read?
- Does it delete, rename, publish, notify, charge, or call external systems irreversibly?
- Is rollback a code revert, a flag flip, a data repair, or a manual operation?

Finding shape:

```text
Rollback - [P0/P1/P2]: Reverting after deploy is [safe/destructive/partial] because [evidence]. Action: [rollback strategy].
```

### Domain and Terminology Confusion

Failure: the plan encodes the wrong concept because terms differ between user, code, docs, and UI.

Ask:

- Does the plan introduce new nouns or reuse overloaded domain terms?
- Do `CONTEXT.md`, code names, UI labels, and the user mean the same thing?
- Are synonyms being treated as separate concepts or separate concepts being collapsed?

Finding shape:

```text
Domain - [P0/P1/P2]: The plan uses [term] to mean [meaning], but [source] uses it as [different meaning]. Action: [rename, glossary update, or behavior clarification].
```

## Output by Tier

Tiny:

- Run this mentally.
- Emit only real findings.
- If there are no material findings, add one assumption sentence: `Pre-mortem found no material risk because this is [specific low-risk reason].`

Standard:

- Include P0 and P1 findings in the plan.
- Include only important P2 findings as assumptions.
- Do not list every N/A category.

High-risk:

- Include a compact `Pre-Mortem Findings` section for real findings.
- No unresolved P0 findings may remain.
- P1 findings must map to a migration, compatibility, fallback, test, rollout, or rollback step.

## Sanity Checks

- If a non-trivial plan has no findings, re-check Scope Blast Radius, Testability Gaps, and Rollback Traps.
- If findings are generic, redo them with file paths, data shapes, config names, or explicit assumptions.
- If the pre-mortem makes the plan too long, keep the risk action and remove category narration.
