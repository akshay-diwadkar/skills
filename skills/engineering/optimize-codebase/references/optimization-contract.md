# Optimization Contract

Use this contract to turn a named workflow into one evidence-backed candidate
and one bounded handoff. The machine fields in
[optimization-contract.json](optimization-contract.json) and
[handoff-contract.json](handoff-contract.json) are authoritative when this
prose differs.

## Selection

- Paths are `fast` or `full`; scopes are `targeted` or `sweep`; stages are
  `plan` or `implementation`.
- `targeted` scope follows a named pain and may inspect only the relevant
  surface; `sweep` is allowed only when repository-wide discovery is explicit.
- Choose `fast` only when every [fast-path](fast-path.md) criterion is already
  proved: one authorized change, one file and symbol, bounded behavior, local
  verification, and a reversible rollback.
- Use `full` whenever any criterion is unproved. Establish a baseline, compare
  independent candidates, and promote exactly one winner.

## Evidence gates

Every candidate needs a target, impact, confidence, effort, risk, blast radius,
independence, verification strength, rollback, operational cost, and cited
evidence. A candidate is promoted only when behavior, compatibility,
verification, rollback, and decision gates are all affirmative. Missing,
neutral, contradictory, or inconclusive evidence remains visible as a
deferment or rejection; it never becomes an implicit approval.

## Authority and handoff

Local evidence selects the mechanism. Ecosystem material may validate a chosen
mechanism but cannot override repository facts. Implementation remains unauthorized
until the user explicitly requests it. A plan handoff contains one
winner, residual risks, deferments, verification commands, and rollback state.
The sealer must receive the complete agent-authored report and return one
canonical result; do not resurrect a multi-stage validation dance.
