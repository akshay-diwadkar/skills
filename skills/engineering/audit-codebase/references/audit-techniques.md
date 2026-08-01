# Audit Techniques

Use these techniques only for the risk surfaces selected by the audit contract.
The primary agent owns coverage, reconciliation, acceptance, and publication.

## Surface probes

- Correctness: trace state transitions, boundary conditions, retries, timeouts,
  partial completion, and error handling through their callers and tests.
- Security: inspect trust boundaries, authentication/authorization, secret
  handling, injection, unsafe deserialization, dependency exposure, and
  sensitive logging.
- Performance: identify hot paths, repeated I/O, unbounded work, lock or queue
  contention, and missing measurement before proposing optimization.
- Tests and maintainability: find untested branches, misleading fixtures,
  duplicated policy, ownership friction, and drift between contracts and code.

For every candidate, disconfirm it with an alternate explanation, reproduce the
impact where safe, and cite the smallest current evidence. Use ecosystem
material only when a local finding selects a versioned dependency or platform
question; record compatibility and operational constraints rather than treating
external guidance as authority.

## Delegated review

Category scouts may inspect independent read-only slices, but the primary agent
must reconcile omissions and contradictions against authoritative source. A
missing, malformed, blocked, redirected, or over-budget result is an omission;
retry the affected contract once sequentially, then record a terminal omission
and block completion if it fails again.
