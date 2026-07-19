# Cognitive Protocols

Use these procedures only while building the corresponding v2 records.

## Evidence and root cause

1. Search for the requested function, route, command, type, or behavior and read the full definition.
2. Record its signature, branches, errors, external calls, and side effects.
3. Trace one real path from the most common caller to the first I/O boundary and observable result.
4. Search the whole repository for direct callers, re-exports, mocks, fixtures, config/schema keys, generated artifacts, and docs.
5. Read the nearest analogue and record how it handles validation, authorization, errors, logging, and output.
6. Compare code with tests, comments, and docs; record contradictions rather than choosing silently.

For a bug, prove the symptom and follow evidence-backed “why” links until the next link would be speculation. The deepest supported cause is the root cause. Reject a symptom-only patch unless containment is explicitly required.

Stop when current behavior, root cause where relevant, boundary, callers, invariants, side effects, gaps, and contradictions are known. Convert only useful observations into canonical `F-n` records.

## Request-to-evidence reconciliation

After grounding, compare the framed request with the evidence. Maintain a temporary ledger with one row per possible gap:

`request statement | repository evidence | gap and planning consequence | options | recommendation and reason | status`

Record conflicts, missing requirements, scope mismatches, hidden constraints, undefined success or failure behavior, and acceptance gaps. Mark a gap `blocking` only when its resolution could change the outcome, scope, user-visible behavior, shared interface, risk, rollout, or acceptance criteria. Resolve repository facts through further exploration and decide low-impact reversible details from precedent; do not ask the user about either.

For each blocking gap:

1. Group at most three closely related gaps in one round.
2. State the relevant request language and cite the grounded `F-n` evidence that exposed the gap.
3. Explain the concrete decision or plan surface affected.
4. Offer two to four mutually exclusive options when the answer space can be bounded. Identify one as recommended and justify it from repository precedent, constraints, compatibility, and the smallest correct change.
5. Ask a scoped free-text question only when honest alternatives cannot be enumerated.
6. Record the answer, update the request baseline, and re-explore whenever the answer changes the change boundary or invalidates evidence.
7. Repeat until every ledger row is resolved or reclassified as non-blocking. Do not impose a lifetime question limit.

Then present an alignment recap containing the resolved goal, measurable success criteria, audience, in-scope and out-of-scope behavior, invariants, user-visible behavior, public/shared contracts, constraints, and key decisions. Require explicit confirmation. Treat corrections as new input: update the baseline, re-run reconciliation, and seek confirmation again. Confirmation establishes shared planning intent, not authorization to implement.

After confirmation, translate resolved gaps into the existing `SC-n`, `D-n`, and `C-n` records and discard the temporary ledger. Do not add gap-ledger records or headings to the final plan contract.

## Interface changes

For a public/shared function, API, command, type, event, or schema:

1. Copy the complete current shape: names, parameters, types, defaults, returns/errors, serialization, and nullability.
2. Write the complete proposed shape, not a prose delta.
3. Enumerate every consumer and generated surface.
4. Resolve old caller/new interface, new caller/old interface, and new/new behavior.
5. Specify rollout order and rollback behavior when versions can overlap.

Stop when no compatibility cell or generated consumer is unresolved.

## Propagation

For every existing `CH-n` anchor, search direct calls/imports, re-exports, fixtures/mocks, config/schema, generated surfaces, deployment hooks, and docs. Record an update/no-update decision for each material reference and assign every required update to a `CH-n`.

## Decision completeness

Before finalization, scan for deferred language, missing else/error/default branches, untyped or nullable interface fields, tests without exact inputs/outputs, and backward implementation ordering. Resolve each material gap; retain only explicitly low-impact reversible assumptions.
