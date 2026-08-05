# Task guidance

Read only the matching branch.

- Feature: entry → ownership → tests; name defaults, errors, ordering, preserved
  behavior.
- Bug fix: root-cause branch, smallest correction, regression that fails before
  the fix.
- Refactor: preserve behavior; enumerate callers, re-exports, fixtures, contracts.
- Migration: old/new shapes, mixed-version behavior, deploy order, interrupted
  state, rollback/roll-forward.
- Operational: rollout trigger, observability signal, recovery, blast radius.
- Public contract/schema: consumers, compatibility window, generated/config
  companions.
- Dependency/config: owning manifest, defaults/failures, downstream consumers.
- Generated artifacts: generator ownership, exact outputs, regeneration checks.
- Security: principal, trust boundary, authz owner, denial, cross-boundary tests.
- Concurrency: shared state, atomicity, retries, idempotency, worst interleaving,
  reconciliation.
- External/irreversible: API version, auth, timeouts, retries, rate limits,
  ambiguous success, idempotency, compensation.

Add records only for applicable surfaces; do not manufacture sections.
