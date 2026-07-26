# V5 example rules

Use `scripts/scaffold_plan.py` as the only scaffold. Fill facts with current
fingerprints, preserve all provisional domains or add grounded `X-n` dismissals,
and finalize only after `scripts/check_plan.py --require-finalized` passes.

An existing `CH-n` always cites a same-path `F-n`; traceability uses exact table
rows; standard and high-risk plans place a typed execution blueprint inside
`Implementation Specification`.

## Tiny local fix

Use one `SC` with observable `given/when/then/unchanged`, one same-anchor
function fact, one `CH`, and one exact `SC -> CH -> T` trace row. A null guard
that preserves non-null normalization is tiny only when no caller changes.

## Standard propagation

For a parser rename, inventory the library export, CLI, fixture, and mock as
separate `P` records. Use an interface blueprint immediately after the owner
changes; every consumer disposition has an owning change or factual reason.

## High-risk contract

For an event-schema migration, classify public-contract and durable-state,
create every matrix obligation, and use a compatibility-table blueprint that
shows old writer/new reader, new writer/old reader, and interrupted rollout.

## Re-tier and dismissal

Re-tier from tiny to standard after finding a second boundary. Remove a
provisional concurrency domain only with `X-n` evidence showing request-local
state and a concrete dismissal reason; never simply delete it.

## Generated, security, and concurrency

Use `generated-from` plus a generator owner instead of editing generated output.
Security obligations name principal, tenant, authorization order, denial, and
cross-tenant tests. A concurrency blueprint names the worst interleaving,
idempotency key, timeout/duplicate outcome, and reconciliation.

## Questions and exact failures

Ask only material user questions, for example: “Should an existing token remain
valid after tenant transfer?”  `D-1: selected: cleaner` fails
`decision.concrete`; `A-security: done` fails `attack.format`; an old marker
fails `contract.unsupported`. Generate receipts only through the finalizer.
