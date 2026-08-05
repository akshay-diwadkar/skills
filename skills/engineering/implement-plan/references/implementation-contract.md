# Implementation Contract

The machine fields in [implementation-contract.json](implementation-contract.json)
are authoritative. This document is the compact execution contract for one
sealed plan and one implementation bundle.

## Intake and ownership

Accept a sealed plan-contract v6 or v7 plan with a supported tier, complete typed
record graph, current repository binding, and matching receipt. Reject
ambiguous, unsupported, unfinalized, receipt-mismatched, or materially
contradicted plans; route semantic gaps back to `plan-change`. The plan limits
behavior changes, while current repository evidence determines local form.

For v7 plans, prepare/intake and finalization require a deterministic
`change_order` from `CH.depends_on` (tie-break by numeric CH id). The bundle
schema requires matching `plan.change_order`, `workspace.change_order`, and
per-target `ch_id` / `depends_on`. That declared order is the scaffold and proof
order. Completion may follow any valid topological order: every planned CH
exactly once, each only after its `depends_on` predecessors. Completing a
dependent before its prerequisites fails sealing. Seal also requires every
planned `T` in a passed verification row and empty `unresolved_changes` /
`unresolved_tests`. For historical v6 plans, preserve record declaration order
as `change_order` and do not invent obligation fields.

The primary agent owns edits, scope reconciliation, and completion. Preserve
unrelated dirty work byte-for-byte. Do not edit a dirty target without explicit
authorization, and stop on a concurrent target change. Only planned paths may
be touched, except where the mechanical propagation gate records an
evidence-backed dependent change.

## Execution and proof

Ground every change in the plan's `CH`, `P`, `B`, `R`, and `T` records. Snapshot
the relevant pre-state, apply records in dependency order, and verify each
planned branch, error, side effect, and test. Tiny work may use one aggregate
change row; standard and high-risk work require one change row per `CH` and a
distinct successful regression row. Attribute failures as pre-existing only
when the identical check failed in the recorded baseline.

The bundle must report changed paths, propagation, exact checks, residual risks,
rollback state, and unresolved records. Seal only after the bundle validator
passes and the receipt is computed from the canonical bundle without its prior
receipt.
