# Adversarial Verification

Attack instructions, not intentions. Record each required attack as `repaired`, `dismissed`, or `not-applicable` with concrete evidence. Never create findings to satisfy a count.

## Reality check

Re-open every citation, existing `CH-n` anchor, signature, interface shape, and unchanged claim. Confirm every `T-n` has exact given and expected fields and every Traceability row points to defined IDs.

## A1 — Forgotten caller

For every changed symbol, search direct callers/imports, re-exports, fixtures/mocks, config/schema, generated clients, and docs. Repair missing propagation ownership.

## A2 — Boundary input

Exercise every new or changed input with applicable null, empty, zero, negative, maximum, invalid type, and unmatched/default cases. Specify exact behavior and tests.

## A3 — Concurrent request

When shared state exists, simulate simultaneous read/modify/write, timeout followed by retry, duplicate delivery, and cancellation. Specify locking, transaction, compare-and-set, or idempotency behavior when needed.

## A4 — Rollback

When durable or external effects exist, assume new code processed real work and is then rolled back. Verify old readers, writers, queued work, cache, and irreversible effects remain safe or have explicit recovery.

## A5 — Scale surprise

When loops, queries, collections, or batches change, test 10× and 100× plausible volume for N+1 I/O, unbounded memory, missing pagination, long transactions, or lock contention.

## A6 — Literal implementation

Read each `CH-n` as a literal implementer. Check that path, symbol, type, branches, errors, ordering, side effects, and caller changes are sufficient to write one materially equivalent implementation. Repair every ambiguity.

## Severity and repair

- P0: data loss, security breach, silent corruption, or unrecoverable state. Finalization is blocked.
- P1: incorrect behavior, broken caller, missing failure handling, or unsafe rollback. Modify the owning `CH-n` and `T-n`.
- P2: non-blocking concern. Keep only with explicit acceptance evidence.

After repairs, compare success criteria with invariants, pseudocode/interface shapes with test expectations, propagation with implementation ownership, and risks with actual mitigations. Finalize only with no unresolved P0/P1.
