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
