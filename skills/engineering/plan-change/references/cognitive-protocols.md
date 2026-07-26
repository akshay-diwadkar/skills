# Cognitive Protocols

Use these procedures while producing v5 records. Keep working notes out of the final plan.

## Evidence and Root Cause

1. Read the requested function, route, command, type, or behavior in full.
2. Record its signature, branches, errors, external calls, and side effects.
3. Trace one common caller through the first I/O boundary to the observable result.
4. Search direct callers, re-exports, mocks, fixtures, config/schema keys, generated artifacts, deployment hooks, and docs.
5. Read the nearest analogue and compare validation, authorization, errors, logging, state, and output.
6. Record contradictions between code, tests, comments, docs, and configuration.

For a bug, follow evidence-backed "why" links until the next link would be speculation. The deepest supported cause is the root cause. Reject a symptom-only fix unless containment is explicitly requested.

Complete grounding when current behavior, root cause where applicable, boundary, consumers, invariants, side effects, contradictions, and test gaps are known. Convert only plan-relevant facts into strict `F-n` records with the required path, line range, anchor, excerpt hash, and file hash.

Never estimate, copy from stale notes, or invent either hash. Immediately before
writing an `F-n`, run `scripts/hash_excerpt.py` (or an exactly equivalent shell
command) against the current file and the exact inclusive range. Recompute both
hashes whenever the file content or cited range changes.

## Request Reconciliation

Maintain a temporary ledger:

`request | evidence | planning consequence | options | recommendation | status`

Explore further for repository facts. Resolve reversible implementation details from local precedent. A gap is blocking only when it can change observable behavior, scope, a shared contract, durable state, security, rollout, or acceptance criteria.

For each blocking gap, cite the evidence, explain the affected success criterion, decision, change, or test, offer mutually exclusive options when honest, and recommend the smallest compatible choice. Re-sweep boundaries changed by the answer. Seek explicit confirmation only for these material gaps.

Discard the ledger after resolved intent is represented by `SC-n`, `D-n`, `CH-n`, and `T-n` records.

## Interfaces and Propagation

For every changed public or shared function, API, command, type, event, or schema, specify complete current and proposed shapes: names, parameters, types, defaults, return/errors, serialization, and nullability. Account for old/new combinations and generated consumers.

For every existing changed anchor, adapt these literal search templates from the
repository root:

```bash
# Direct callers, imports, and other symbol references.
rg -n --glob '!*.lock' '\bSYMBOL\b|from .* import .*SYMBOL|import .*SYMBOL' .

# Re-exports and public package surfaces.
rg -n '__all__|export .*SYMBOL|from .* import .*SYMBOL|SYMBOL\s*=' \
  .

# Fixtures, mocks, config/schema, generated output, deployment, and docs.
rg -n -i --glob '*.{py,js,ts,json,yaml,yml,toml,md}' \
  'SYMBOL|CONFIG_KEY|fixture|mock|generated|deploy' .
```

Replace `SYMBOL`, `CONFIG_KEY`, and search roots with exact repository terms;
inspect results rather than treating a textual match as proof. Assign each
required update a `CH-n`. Ground every material result with `F-n`, then record
each changed, test-only, generated, unchanged, or out-of-scope surface as a
typed `P-n` disposition with its `CH-n` owner or `F-n` reason.

Before finalization, scan for deferred language, missing else/error/default branches, unresolved nullability, tests without exact expectations, and backwards dependency ordering. Resolve every material gap.
