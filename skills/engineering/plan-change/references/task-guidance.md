# Task guidance

Read only the matching branch.

- Feature: trace the new behavior from entry point through ownership and tests;
  name defaults, errors, ordering, and preserved behavior.
- Bug fix: identify the root-cause branch and the smallest behavior correction;
  include a regression test that fails before the fix.
- Refactor: preserve observable behavior and enumerate agent-identified callers,
  re-exports, fixtures, and contract surfaces.
- Public contract or migration: describe old/new shapes, mixed-version behavior,
  deployment order, interrupted state, and rollback or roll-forward.
- Security: identify principal, tenant/trust boundary, authorization owner,
  denial behavior, and cross-boundary tests.
- Concurrency: identify shared state, atomicity/lock boundary, retries,
  idempotency identity, worst interleaving, and reconciliation.
- External integration or irreversible effect: cover API version,
  authentication, timeouts, retry classes, rate limits, ambiguous success,
  idempotency, and compensation/reconciliation.

Add records only for applicable surfaces. Do not manufacture decisions,
propagation, or risks to satisfy a template.
