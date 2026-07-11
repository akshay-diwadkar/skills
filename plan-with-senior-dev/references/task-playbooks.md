# Task Playbooks

Read only the sections matching the task. Apply multiple sections when the change crosses categories.

## Feature

- Prove the user entrypoint, orchestration path, state boundary, output, and nearest analogous feature.
- Decide empty, loading, invalid, unauthorized, partial-success, and retry behavior.
- Trace UI/API/command contracts through core logic, persistence, telemetry, and tests.
- Complete when every user-visible state maps to implementation and verification.

## Bug Fix

- Reproduce or prove the symptom from a test, log, code path, or minimal command.
- Trace 5 Whys only while each answer remains evidenced; stop before speculation.
- Name the smallest root cause and reject the nearest symptom-only patch.
- Add a regression case that fails for the root cause, not just the reported example.
- Complete when the plan explains why the bug occurs, why the fix reaches the cause, and why adjacent valid behavior remains unchanged.

## Refactor

- State the behavior-preservation contract and measurable structural goal.
- Trace all direct/transitive references, tests, mocks, fixtures, snapshots, generated artifacts, and extension points.
- Prefer a tracer-bullet move that keeps the system runnable between steps.
- Do not combine behavior change unless separately identified and approved.
- Complete when each step is independently reviewable and rollback does not strand callers between old and new shapes.

## Migration or Persisted Data

- Inspect schema, readers, writers, validators, backfills, indexes, caches, queued payloads, and deployment ordering.
- Specify old-read/new-read and old-write/new-write compatibility during mixed deployment.
- Define preflight counts, dry-run behavior, batches/checkpoints, idempotency, monitoring, abort thresholds, and data rollback limits.
- Never claim rollback if destructive transformation or external publication makes it impossible; specify forward recovery instead.
- Complete when code, data, mixed-version, and operational recovery are explicit.

## Public Contract

- Inspect the current schema/signature, versioning policy, clients, generated SDKs, fixtures, docs, and compatibility tests.
- Show the complete proposed request/response/event/command/type shape.
- Specify unknown-field, missing-field, default, validation, error, deprecation, and old-client behavior.
- Complete when consumers can migrate without discovering an unstated wire decision.

## Security or Authorization

- Identify trust boundaries, principal/tenant identity, permission source, validation order, secret handling, audit behavior, and information leakage.
- Test allowed, denied, unauthenticated, cross-tenant, stale-permission, malformed-input, and enumeration cases.
- Fail closed unless current policy explicitly requires otherwise.
- Complete when every data access and side effect has an authorization owner and denial behavior.

## Concurrency or Ordering

- Identify shared state, transaction/lock boundary, retry source, duplicate delivery, timeout, cancellation, and reentrancy.
- Specify invariants before algorithms. Show interleavings that would violate them.
- Decide idempotency keys, compare-and-set/version checks, ordering guarantees, and recovery after partial completion.
- Complete when retries, duplicates, and the worst material interleaving preserve invariants.

## External Integration

- Verify version-matched authoritative behavior for auth, schemas, pagination, rate limits, idempotency, timeouts, retries, and error classes.
- Trace irreversible effects such as charges, messages, notifications, or remote writes.
- Specify timeout budgets, retry eligibility, deduplication, circuit/fallback behavior, observability, reconciliation, and sandbox/contract tests.
- Complete when dependency unavailability, malformed responses, throttling, duplicate requests, and partial remote success have explicit behavior.

