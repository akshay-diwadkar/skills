# Cognitive Protocols

Use these procedures while producing v4 records. Keep working notes out of the final plan.

## Evidence and Root Cause

1. Read the requested function, route, command, type, or behavior in full.
2. Record its signature, branches, errors, external calls, and side effects.
3. Trace one common caller through the first I/O boundary to the observable result.
4. Search direct callers, re-exports, mocks, fixtures, config/schema keys, generated artifacts, deployment hooks, and docs.
5. Read the nearest analogue and compare validation, authorization, errors, logging, state, and output.
6. Record contradictions between code, tests, comments, docs, and configuration.

For a bug, follow evidence-backed "why" links until the next link would be speculation. The deepest supported cause is the root cause. Reject a symptom-only fix unless containment is explicitly requested.

Complete grounding when current behavior, root cause where applicable, boundary, consumers, invariants, side effects, contradictions, and test gaps are known. Convert only plan-relevant facts into strict `F-n` records with the required path, line range, anchor, excerpt hash, and file hash.

## Request Reconciliation

Maintain a temporary ledger:

`request | evidence | planning consequence | options | recommendation | status`

Explore further for repository facts. Resolve reversible implementation details from local precedent. A gap is blocking only when it can change observable behavior, scope, a shared contract, durable state, security, rollout, or acceptance criteria.

For each blocking gap, cite the evidence, explain the affected success criterion, decision, change, or test, offer mutually exclusive options when honest, and recommend the smallest compatible choice. Re-sweep boundaries changed by the answer. Seek explicit confirmation only for these material gaps.

Discard the ledger after resolved intent is represented by `SC-n`, `D-n`, `CH-n`, and `T-n` records.

## Interfaces and Propagation

For every changed public or shared function, API, command, type, event, or schema, specify complete current and proposed shapes: names, parameters, types, defaults, return/errors, serialization, and nullability. Account for old/new combinations and generated consumers.

For every existing changed anchor, search calls/imports, re-exports, fixtures/mocks, config/schema, generated surfaces, deployment hooks, and docs. Assign each required update a `CH-n`; record every material unchanged, generated, test-only, out-of-scope, or changed surface as a `P-n` disposition with its owner or evidence.

Before finalization, scan for deferred language, missing else/error/default branches, unresolved nullability, tests without exact expectations, and backwards dependency ordering. Resolve every material gap.
