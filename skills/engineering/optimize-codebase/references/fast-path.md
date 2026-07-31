# Fast Path

Use the fast path only when every criterion is already proved. Otherwise route
to `full`; never ask the user to weaken a criterion.

## Eligibility

1. The current request explicitly authorizes implementation.
2. Scope is exactly one existing tracked file and one named existing symbol.
3. One independently measurable mechanism completely addresses the request.
4. Protected behavior, compatibility, threshold, verification, and rollback are unambiguous.
5. Confidence is high and effort, risk, and blast radius are low.
6. No public API, schema, persistence, security, concurrency, external effect, deployment, generated output, dependency, shared configuration, or cross-module propagation can change.
7. The target has no overlapping dirty-worktree change.
8. A comparable measurement or complete bounded-static baseline exists and post-change verification is runnable.

## Artifact and execution

Scaffold `path=fast`, `scope=targeted`, and `stage=implementation`. The artifact
contains exactly one `F-n`, `B-n`, and `C-n`. `C-1` must be `quick-win`, affirm
every eligibility key, cite only `F-1` and `B-1`, carry the literal
`path:symbol`, and define mechanism, threshold, verification, expected result,
and rollback.

After validation, apply only that mechanism and run the embedded verification.
Compare against `B-1`. Revert the introduced patch if behavior regresses or the
result is neutral, worse, or inconclusive.

Complete when the authorized patch and verification are attributable to `C-1`,
or the run has routed to `full`.
