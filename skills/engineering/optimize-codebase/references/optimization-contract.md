# Optimization Handoff Contract

Turn one named workflow into one evidence-backed decision for `plan-change`.
The machine fields in [optimization-contract.json](optimization-contract.json)
are authoritative.

## Selection

- Use `targeted` for a named pain and `sweep` only for explicit repository-wide discovery.
- Establish a measured or bounded baseline, compare independent candidates, and select one winner or a terminal state.
- Set `H-1 next` to exactly `plan-ready`, `needs-evidence`, or `no-change`.
- A `plan-ready` handoff names one eligible candidate; terminal states preserve exact evidence or revisit conditions.

## Evidence gates

Every candidate records target, impact, confidence, effort, risk, blast radius,
independence, verification strength, rollback requirement, operational cost,
and cited evidence. Missing or inconclusive evidence remains a deferment or
rejection.

## Boundary

Local evidence selects the mechanism. This skill never patches the repository,
orders file edits, writes execution tests, or routes directly to
`implement-plan`. The sealer atomically emits only `optimization-handoff.md`;
`plan-change` owns the separate implementation blueprint.
