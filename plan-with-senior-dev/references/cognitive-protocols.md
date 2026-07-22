# Cognitive Protocols

Use these procedures while producing v3 records. Keep their working notes out of the final plan.

## Evidence and Root Cause

1. Read the requested function, route, command, type, or behavior in full.
2. Record its signature, branches, errors, external calls, and side effects.
3. Trace one common caller through the first I/O boundary to the observable result.
4. Search direct callers, re-exports, mocks, fixtures, config/schema keys, generated artifacts, deployment hooks, and docs.
5. Read the nearest analogue and compare validation, authorization, errors, logging, state, and output.
6. Record contradictions between code, tests, comments, docs, and configuration.

For a bug, follow evidence-backed “why” links until the next link would be speculation. The deepest supported cause is the root cause. Reject a symptom-only fix unless containment is explicitly requested.

Complete grounding when current behavior, root cause where applicable, boundary, consumers, invariants, side effects, contradictions, and test gaps are known. Convert only facts that affect the plan into `F-n` records.

## Request Reconciliation

Maintain a temporary ledger:

`request | evidence | planning consequence | options | recommendation | status`

Explore further for repository facts. Resolve reversible implementation details from local precedent. Mark a gap blocking only when it can change observable behavior, scope, a shared contract, durable state, security, rollout, or acceptance criteria.

For each blocking gap, cite the evidence, explain the affected plan surface, offer mutually exclusive options when honest, and recommend the smallest compatible choice. Re-explore boundaries changed by the answer. Seek explicit confirmation only for these material gaps.

Discard the ledger after translating resolved intent into success criteria, decisions, and constraints.

## Interfaces and Propagation

For every changed public/shared function, API, command, type, event, or schema, show the complete current and proposed shapes: names, parameters, types, defaults, return/errors, serialization, and nullability. Account for old/new combinations and generated consumers.

For every existing changed anchor, search calls/imports, re-exports, fixtures/mocks, config/schema, generated surfaces, deployment hooks, and docs. Assign every required update to a `CH-n`; record why material no-update surfaces remain safe.

Before finalization, scan for deferred language, missing else/error/default branches, unresolved nullability, tests without exact expectations, and backward dependency ordering. Resolve every material gap.
