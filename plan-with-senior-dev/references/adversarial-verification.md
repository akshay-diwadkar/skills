# Adversarial Verification

Run after a complete draft. Attack instructions, not intentions. Repair the owning section for every material finding.

## Pre-Attack Reality Check

Before running any attack, verify your own plan's factual claims. Fix discrepancies NOW — do not proceed to attacks with a factually incorrect plan.

1. **Re-read every `file:line` citation.** Open each cited file and verify the line contains what you claimed. If the code has changed or you misread it, correct the plan.
2. **Re-read every "unchanged" claim.** For each behavior you claimed will not change, verify your proposed changes do not affect it. Trace through the call path.
3. **Re-read every function signature.** Does the signature in your plan (parameters, types, return type) match the actual code? Copy-paste from the source if uncertain.
4. **Count your CH-n items.** Does each one name a specific file AND a specific symbol (function, class, method, config key)? If any CH-n says "update relevant files" or "make necessary changes," replace it with the exact file and symbol.
5. **Count your T-n items.** Does each one have an exact input AND an exact expected output? If any T-n says "test that it works" or "verify correctness," replace it with the specific assertion.

Proceed to attacks only when all citations, signatures, and traceability IDs are verified.

## Mandatory Attack Templates

Run every applicable attack. Skip an attack only when you can cite specific evidence that eliminates the vector. "It probably doesn't apply" is not evidence.

### A1: The Forgotten Caller

**Applies when:** Any function, method, type, config key, or schema field is modified or renamed.

**Procedure:**
1. For each changed symbol, grep the entire codebase for references.
2. For each reference found, check: does this caller/consumer handle the new behavior correctly?
3. Check re-exports, barrel files, and module indexes.
4. Check test mocks and fixtures that reference the old shape.
5. Check generated code (SDKs, protobuf, OpenAPI, GraphQL).

**Finding format:**
```
R-n P1 [A1 Forgotten Caller]: Caller at `file:line` passes [old args],
but CH-n changes the signature to [new signature].
Consequence: [TypeError / wrong behavior / silent corruption].
Resolution: Add CH-m to update `file:line` with [exact change].
```

### A2: The Empty/Boundary Input

**Applies when:** Any new parameter, branch, validation rule, or data path is added.

**Procedure:**
1. For each new input/parameter, test with: null, undefined, None, empty string, empty array, empty object, zero, negative number, maximum value, NaN, very long string.
2. For each new branch, verify: is the else/default case specified? What happens when no branch matches?
3. For each new validation rule, verify: what error is returned for invalid input? Is the error message specific?

**Finding format:**
```
R-n P1 [A2 Boundary Input]: When [parameter] is [boundary value],
CH-n at `file:line` will [crash / return wrong value / skip validation].
Consequence: [error message / data corruption / silent failure].
Resolution: Add [guard / default / validation] to CH-n.
```

### A3: The Concurrent Request

**Applies when:** The change touches shared state (database, cache, global variable, queue, file).

**Procedure:**
1. Identify the shared state and its access pattern (read-modify-write, append, delete).
2. Simulate two requests arriving simultaneously. What happens?
3. Simulate a request that succeeds but the response times out, causing a retry.
4. Simulate the operation being delivered twice (at-least-once delivery).

**Finding format:**
```
R-n P1 [A3 Concurrency]: Two concurrent requests to CH-n can both
read [state] as [value], then both write [computed value],
causing [lost update / duplicate record / constraint violation].
Consequence: [data corruption / incorrect count / charge duplication].
Resolution: Add [transaction / lock / CAS / idempotency key] to CH-n.
```

### A4: The Rollback Scenario

**Applies when:** The change involves persisted data, external API calls, schema migrations, or irreversible side effects.

**Procedure:**
1. Assume the new code is deployed successfully and processes real data.
2. Now assume the deployment is rolled back to the old code.
3. Can the old code read data written by the new code?
4. Can the old code handle records in the new state/format?
5. Are external effects (API calls, emails, charges) reversible?

**Finding format:**
```
R-n P1 [A4 Rollback]: After rollback, old code at `file:line` reads
[new data format] and [crashes / misinterprets / corrupts].
Consequence: [service outage / data loss / incorrect billing].
Resolution: [dual-read strategy / backward-compatible format / feature flag] in CH-n.
```

### A5: The Scale Surprise

**Applies when:** The change involves loops, queries, in-memory collections, or batch processing.

**Procedure:**
1. What is the current data volume? What is 10x? 100x?
2. Does the plan load all items into memory? Is there pagination?
3. Does the plan execute N queries in a loop (N+1 problem)?
4. Does the plan hold a lock/transaction during a potentially long operation?

**Finding format:**
```
R-n P1 [A5 Scale]: CH-n loads all [items] into memory at `file:line`.
At 10x volume ([N] items), this consumes [estimated memory].
Consequence: [OOM / timeout / lock contention].
Resolution: Add [pagination / streaming / batching] to CH-n with batch size [N].
```

### A6: The Literal Implementation Test

**Applies when:** Every plan. This is the most important attack.

**Procedure:**
1. Read the plan as if you are a developer who will follow it word-for-word.
2. At each implementation step, ask: "Do I have enough information to write the exact code?"
3. Check: are parameter types specified? Return types? Error types? Default values?
4. Check: for each branch in pseudocode, is the else/error case specified?
5. Check: would two developers following this plan independently write the same code?

**Finding format:**
```
R-n P1 [A6 Underspecified]: CH-n says "[vague instruction]" but does not
specify [missing detail]. Two implementers would make different choices.
Consequence: [inconsistent behavior / integration failure].
Resolution: Specify [exact detail] in CH-n.
```

## Cross-Consistency Audit

- Compare every success criterion with every stated invariant; reject mutually exclusive requirements.
- Compare pseudocode branches with test expectations; identical preconditions cannot require incompatible results.
- Compare interface shapes with current citations and compatibility claims.
- Compare propagation entries with implementation steps; every "update required: yes" needs an owner.
- Compare at-risk constraints with tests and rollback.
- Compare risks with actions; actions must appear in implementation or verification, not only the risk list.

## Severity Classification

- **P0**: Blocks finalization. Data loss, security breach, silent corruption, unrecoverable state.
- **P1**: Must modify the plan. Incorrect behavior, missing error handling, broken caller, missing rollback for durable effects.
- **P2**: May remain with evidence and explicit acceptance. Cosmetic, non-blocking performance concern, minor documentation gap.

## Quality Rules for Findings

- Do not manufacture three cosmetic findings. If an attack vector is immaterial, state the exact evidence that eliminates it.
- One real P1 that repairs the plan is more valuable than three keyword-rich bullets.
- Every P0/P1 finding must include: concrete scenario, exact defect in the plan, observable consequence, severity, and resolution with the CH-n/T-n that changes.
- Do not list risks without modifying the plan. A finding without a resolution is incomplete.

## Stop Rule

Finalize only when:
- Pre-attack reality check passed (all citations, signatures, and IDs verified)
- Every mandatory attack template has been run or dismissed with evidence
- No unresolved P0 exists
- Every P1 has changed its owning section
- Every success criterion is traceable to implementation and verification
- Remaining assumptions are low-impact and reversible
