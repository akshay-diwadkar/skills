# Adversarial Planning

Use this reference before finalizing Standard and High-risk plans. The job is to make the plan hostile to accidental breakage: prove what changes, what must not change, how far the blast radius extends, and how the system fails safely.

## Senior Adversary Pass

For each category, write a concrete plan constraint or `N/A - [specific reason]`. Do not leave generic reminders for implementation.

### Invariants

Name the behavior, data shape, public contract, permission rule, performance expectation, or domain meaning that must stay unchanged.

Good constraints:

- `Keep existing unauthenticated requests rejected with the current 401 response shape.`
- `Preserve the current CLI exit codes and stdout format; only stderr gains the new warning.`
- `Do not change persisted enum values or migration history.`

### Blast Radius

Identify who can be affected: importers, callers, routes, jobs, workers, webhooks, subscribers, generated clients, shared helpers, config, schemas, and tests.

If the blast radius is intentionally narrow, say why the nearby surfaces are unaffected. If a shared helper changes, assume the blast radius is wider until evidence proves otherwise.

### Side Effects

State whether the plan touches persistence, network calls, filesystem writes, external APIs, queues, background jobs, browser storage, notifications, billing, or irreversible operations.

If there are no durable or external side effects, say that explicitly in `Rollback Plan` or `Failure Modes`. If there are side effects, state the idempotency, retry, rollback, and old/new compatibility behavior.

### Failure Behavior

For each expected failure path, define the observable result: error type, response, log, retry, fallback, skipped work, rollback, or user-visible state. Do not use `handle errors` without naming the behavior.

### Optimality Guard

Prefer the smallest change that follows local precedent. Add a new abstraction only when the repo already uses the pattern here, or two concrete cases need the same seam now. Reject provider, factory, adapter, registry, or shared-interface plans that exist only to make future work feel tidy.

## Final Check

Before presenting the plan, verify:

- `Scope` names in-scope changes, unchanged invariants, and blast radius.
- `Approach` cites local precedent or explains the exception.
- `Failure Modes` and `Rollback Plan` cover side effects or explicitly state none exist.
- High-risk `Risk` or `Pre-Mortem Findings` gives `Action:` mitigation for every P0/P1 risk.
