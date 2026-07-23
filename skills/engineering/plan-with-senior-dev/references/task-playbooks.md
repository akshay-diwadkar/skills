# Task Playbooks

Read only the sections matching the task. The common evidence sequence lives in `cognitive-protocols.md`; these are task-specific deltas.

## Feature

- Ground the user entry, orchestration path, state mutations, output shape, permission/feature gates, and nearest analogue.
- Decide empty, loading, invalid, unauthorized, partial-success, and dependency-failure behavior.
- Preserve local response, telemetry, and error conventions; avoid a framework for one feature.
- Prefer pseudocode for branching or Mermaid for a flow spanning three or more components.
- Complete when every user-visible state owns a change and exact verification case.

## Bug Fix

- Prove the symptom and deepest evidence-backed cause; identify tests that should have caught it.
- Search analogous code for the same defect class and preserve adjacent valid behavior.
- Reject symptom patches and unrequested input/return/interface widening.
- Prefer pseudocode showing the defective and corrected branch when the cause is not a one-line guard.
- Complete when the plan explains why the bug occurs, why the fix reaches its cause, and why adjacent behavior remains unchanged.

## Refactor

- State the behavior-preservation contract and measurable structural outcome.
- Find direct and transitive consumers, re-exports, mocks, snapshots, generated artifacts, and extension points.
- Keep behavior changes separate and preserve a runnable tracer bullet between dependency-ordered steps.
- Prefer a dependency table or Mermaid graph when symbol movement crosses modules.
- Complete when each step is independently reviewable and rollback strands no consumer.

## Public Contract

- Ground the complete current shape, versioning policy, consumers, generated SDKs, fixtures, docs, and compatibility tests.
- Decide additive/breaking behavior, unknown fields, missing fields/defaults, stable errors, and mixed-version deployment.
- Require complete before/after shapes plus an old/new compatibility table; prose deltas do not qualify.
- Complete when consumers can migrate without discovering an unstated wire decision.

## Security or Authorization

- Ground trust boundaries, principal/tenant identity, permission source, validation order, secret handling, and audit behavior.
- Decide denial semantics, cross-tenant behavior, enumeration resistance, revocation, and time-of-check/time-of-use risk.
- Prefer pseudocode for validation order or Mermaid for a multi-service trust flow.
- Complete when every data access and side effect has an authorization owner and denial test.

## Concurrency or Ordering

- Ground shared state, transaction/lock boundaries, retries, duplicate sources, timeout, and cancellation behavior.
- Decide invariants, idempotency identity, ordering guarantee, partial completion, and reconciliation.
- Require Mermaid sequence/state flow or pseudocode covering the worst material interleaving.
- Complete when retries, duplicates, and concurrent operations preserve the stated invariants.

## External Integration

- Match provider documentation to the installed SDK/API version; ground authentication, limits, timeouts, and irreversible effects.
- Decide retryable errors, idempotency, backoff, fallback, malformed responses, and reconciliation after ambiguous success.
- Prefer Mermaid sequence flow for timeout/retry/reconciliation or pseudocode for response classification.
- Complete when unavailability, throttling, duplicates, malformed responses, and partial remote success have exact behavior and tests.
