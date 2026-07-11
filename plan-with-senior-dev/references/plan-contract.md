# Plan Contract

Use the smallest template that remains decision-complete. Sections may contain compact tables, but every required field must carry real content rather than “N/A” theater.

## Tiny

Use only for one local, reversible behavior with no public API, schema, auth, concurrency, migration, external side effect, or durable domain effect.

```markdown
# [Action-oriented outcome]

## Outcome
[Observable goal and success condition]

## Evidence
- Fact: `path:line` [current behavior]

## Change
[Exact file/symbol, signature when changed, behavior, branches, and preserved invariant]

## Verification
- [Exact input/action] -> [exact output/assertion]
- `[command]` -> [expected result]

## Assumptions
- Low-impact: [reversible assumption, or “None”]
```

## Standard

Use for the default multi-file or multi-layer feature, unclear-cause bug, refactor, or internal interface change.

```markdown
# [Action-oriented outcome]

## Outcome and Scope
- SC-1: [measurable result]
- In scope: [behavior/surfaces]
- Unchanged: [explicit invariants and exclusions]

## Evidence and Decisions
- Fact: `path:line` [current behavior]
- Contradictions: [specific conflict, or checked surfaces and none found]
- Decision: [selected approach] because [constraint/local precedent]
- Rejected: [nearest valid alternative] because [specific drawback]

## Implementation Specification
- CH-1: [dependency-ordered change with exact file/symbol/interface]
```pseudocode
operation(input: Type) -> ResultType:
    [branches, errors, and side effects]
```

## Traceability and Constraints
| Criterion / constraint | Implementation | Verification | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Preserved / modified / at-risk |

Changed symbol -> affected surface
- `path:line` - CH-1 - update required: yes/no - [reason]

## Verification and Risks
- T-1: Given [exact state/input], assert [exact output/side effect/error].
- Command: `[command]` -> [expected result].
- R-1 P1: [scenario, consequence, resolution and owning CH/T].
- Rollback: [concrete revert/disable/restore path and side-effect handling].

## Assumptions
- Low-impact: [assumption, or “None”]
```

## High-Risk

Use the Standard template and add these sections:

```markdown
## Compatibility
[old/new reader, writer, client, event, and deployment-order behavior]

## Migration and Rollout
[preconditions, validation, batching/checkpoints, mixed-version behavior, observability, stop conditions]

## Durable Rollback
[code, data, queued work, cache, and irreversible external-effect recovery]

## Risk Register
- R-1 P0/P1/P2: [scenario and consequence]. Action: [mitigation]. Owner: CH-n/T-n.
```

No unresolved P0 may remain. Every P1 must have an action and verification owner.

## Interface Rules

When any public or shared interface changes, show the complete proposed shape, not a prose delta. Include:

- exact name, parameters, types, defaults, return type, and errors;
- serialization and nullability;
- old/new client behavior and version boundary;
- generated artifacts and downstream consumers;
- validation ownership and stable error representation.

## Traceability Rules

- Define each ID once; references may appear many times.
- Every `SC-n` must appear in implementation traceability and verification.
- Every `CH-n` must name its affected symbol or surface.
- Every `T-n` must contain an exact assertion or observable result.
- Every modified or at-risk `C-n` must map to `CH-n` and `T-n`; add rollback when persistent or external.
- Every `R-n` P0/P1 must map to an action and owner.

## Final Audit

- Are facts cited and assumptions labeled?
- Would two literal implementers choose the same behavior and interfaces?
- Does the plan repair root cause rather than symptoms?
- Do changed symbols cover callers, transitive consumers, tests, config, schemas, generated surfaces, and docs?
- Are mixed-version, retry, duplicate, ordering, partial-failure, and rollback states explicit when relevant?
- Does every success criterion have an implementation step and exact test?
- Can each command’s expected result prove the intended behavior?
- Has every P0/P1 attack changed the plan or been resolved by a user decision?

