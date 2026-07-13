# Task Playbooks

Read only the sections matching the task. Apply multiple sections when the change crosses categories. Each playbook specifies mandatory evidence, key decision points, common traps, and minimum verification.

## Feature

### Evidence Checklist
- [ ] User entry point identified (route, command, UI handler) with `file:line`
- [ ] Orchestration path traced: entry → core logic → persistence → output
- [ ] State boundaries mapped: what is created, read, updated, deleted
- [ ] Output format specified: response shape, status codes, headers, or UI elements
- [ ] Nearest analogous feature found and its pattern recorded with `file:line`
- [ ] Empty, loading, invalid, unauthorized, and partial-success states decided

### Key Decision Points
- Does an analogous feature already exist? Follow its pattern unless a cited constraint requires deviation.
- What happens on partial success (e.g., 3 of 5 items processed)? Decide atomicity: all-or-nothing vs. partial with error report.
- What does the response look like for every non-happy state? Specify exact error codes and messages.
- Is the feature gated (flag, permission, plan tier)? If so, specify the gate check location and denial behavior.

### Common Traps
- **Forgetting the unhappy paths**: Planning only the success flow and leaving error, empty, and unauthorized states to "implementation."
- **Inventing a new pattern**: Building a custom approach when an analogous feature in the same codebase already solves the same problem.
- **Scope creep via abstraction**: Creating a generic framework when the task requires one concrete feature.
- **Missing telemetry/logging**: If analogous features log or emit metrics, the new feature should too.

### Minimum Verification
- Happy path: exact input → exact output
- At least one error path: invalid input → exact error response
- Authorization: unauthorized request → exact denial response
- Empty state: no data → exact empty response
- If analogous feature has tests, new feature's tests should cover the same scenarios

### Complete When
Every user-visible state maps to an implementation step and a verification case.

---

## Bug Fix

### Evidence Checklist
- [ ] Symptom proven from test, log, code path, or minimal command with `file:line`
- [ ] Exact line where incorrect behavior occurs identified (`file:line`)
- [ ] Expected behavior stated with evidence (test, doc, spec, or user requirement)
- [ ] Call path from trigger to symptom traced (every hop cited with `file:line`)
- [ ] Existing tests checked: is there a test that should catch this? Is it wrong or missing?

### 5-Whys Protocol
At each level, before going deeper:
1. State the "why" as a concrete code observation, not speculation
2. Cite the `file:line` that proves this "why"
3. If no evidence supports the next "why", STOP — you have reached speculation
4. The root cause is the deepest "why" with evidence

### Key Decision Points
- Is the symptom location the same as the root cause location? If not, fix the root cause.
- Does the root cause affect analogous functions? Search for the same pattern elsewhere.
- Should the fix include the reported example only, or the entire class of inputs?

### Common Traps
- **Symptom patching**: Fixing where the error surfaces instead of where the defect originates.
- **Single-example regression test**: Writing a test for only the reported input, missing the broader class.
- **Assuming the report is complete**: The reported example may be one of several triggers. Search for other inputs that hit the same code path.
- **Test that was wrong**: Sometimes a passing test encodes incorrect expectations. Check if existing tests assert the wrong behavior.

### Minimum Verification
- Regression test that fails BEFORE the fix and passes AFTER
- Test targets the root cause, not just the reported symptom
- Adjacent valid behavior verified unchanged (cite existing passing tests)

### Complete When
The plan explains why the bug occurs, why the fix reaches the root cause, and why adjacent valid behavior remains unchanged.

---

## Refactor

### Evidence Checklist
- [ ] Behavior-preservation contract stated explicitly
- [ ] Measurable structural goal defined (e.g., "eliminate duplication between X and Y", "reduce module coupling")
- [ ] All direct references found with `file:line`
- [ ] All transitive references found (re-exports, mocks, fixtures, snapshots, generated artifacts)
- [ ] Extension points identified (plugins, hooks, config-driven behavior)

### Key Decision Points
- Can each step be independently reviewed and tested? If not, break it further.
- Is the refactor behavior-preserving or does it intentionally change behavior? These must be separated.
- Does the refactor change any public or shared interface? If so, apply the Interface Change Protocol.

### Common Traps
- **Combining behavior change with refactor**: Sneaking a bug fix or feature into a refactor. These must be separate, identified changes.
- **Breaking the tracer bullet**: Making all changes at once instead of keeping the system runnable between steps.
- **Missing transitive consumers**: Renaming a symbol without updating its re-export, mock, or snapshot.
- **Stranding callers**: During a multi-step refactor, leaving callers pointing to old shapes between steps.

### Minimum Verification
- All existing tests pass after each step (not just after the final step)
- No new behavior is introduced (diff should show only structural changes)
- Rollback does not strand callers between old and new shapes

### Complete When
Each step is independently reviewable, the system is runnable between steps, and rollback does not strand callers.

---

## Public Contract or API Change

### Evidence Checklist
- [ ] Current schema/signature fully documented with `file:line`
- [ ] Versioning policy identified (semantic versioning, URL versioning, none)
- [ ] All consumers enumerated: clients, generated SDKs, fixtures, docs, compatibility tests
- [ ] Complete proposed request/response/event/command/type shape written in a code block

### Key Decision Points
- Is this additive (new field/endpoint) or breaking (renamed/removed field)?
- What is the unknown-field policy? (Ignore, reject, pass through)
- What is the missing-field policy? (Default value, error, null)
- How are old clients handled during rollout? (Version negotiation, backward compatibility, deprecation period)

### Common Traps
- **Prose delta instead of full shape**: "Add a status field" without showing the complete interface. Always show the full before and after.
- **Forgetting generated clients**: OpenAPI specs, protobuf definitions, GraphQL schemas, and SDK generators that depend on the current shape.
- **No default for new fields**: Adding a required field breaks every existing caller that does not send it.
- **Unstated error contract**: New validation rules produce new error codes that existing clients do not handle.

### Minimum Verification
- Old client + new server: must work (or explicit migration plan)
- New client + old server: must work (or explicit deployment ordering)
- Unknown fields: tested
- Missing fields: tested with specified defaults
- Deprecation: tested with warning/error behavior

### Complete When
Consumers can migrate without discovering an unstated wire decision.

---

## Security or Authorization

### Evidence Checklist
- [ ] Trust boundaries identified with `file:line` (where user input enters, where privileged operations occur)
- [ ] Principal and tenant identity sources identified
- [ ] Permission/role source and validation order documented
- [ ] Secret handling verified (no plaintext secrets in logs, responses, or error messages)
- [ ] Audit logging behavior documented

### Key Decision Points
- What is the denial behavior? (Same response as not-found to prevent enumeration, or explicit 403?)
- What is the validation order? (Authenticate → authorize → validate → execute)
- Are there cross-tenant scenarios? (User A accessing User B's resources)
- Is there time-of-check-to-time-of-use risk? (Permission checked, then revoked before action completes)

### Common Traps
- **Authorizing after the action**: Checking permissions after the mutation has already occurred.
- **Leaking existence**: Returning 403 (forbidden) instead of 404 (not found) reveals that the resource exists to unauthorized users.
- **Cross-tenant data access**: Loading a resource by ID without scoping to the current tenant.
- **Stale permissions**: Caching permissions and not invalidating when roles change.

### Minimum Verification
- Allowed: authorized user can perform the action
- Denied: unauthorized user receives the correct denial response
- Unauthenticated: request without credentials receives 401
- Cross-tenant: user A cannot access user B's resources
- Stale permission: recently-revoked permission is denied
- Malformed input: does not bypass authorization

### Complete When
Every data access and side effect has an authorization owner and denial behavior.

---

## Concurrency or Ordering

### Evidence Checklist
- [ ] Shared state identified with `file:line` (database rows, cache entries, in-memory globals, queues)
- [ ] Transaction/lock boundaries identified
- [ ] Retry sources identified (client retry, queue retry, cron re-execution)
- [ ] Timeout and cancellation behavior documented

### Key Decision Points
- What invariants must hold across concurrent operations? State them before choosing algorithms.
- What is the idempotency strategy? (Idempotency key, compare-and-set, version check, deduplication)
- What is the ordering guarantee? (Total order, causal order, eventual consistency, none)
- What happens on partial completion? (Rollback, compensating transaction, retry)

### Common Traps
- **Read-modify-write without lock**: Reading a value, computing a new one, and writing it back without a transaction or CAS.
- **Retry amplification**: A retry that triggers the same operation multiple times without idempotency protection.
- **Duplicate delivery**: Assuming a queue or webhook delivers exactly once when it delivers at-least-once.
- **Timeout masking success**: An operation that succeeds but the caller times out and retries, causing duplication.

### Minimum Verification
- Two concurrent operations: invariants preserved
- Retry after timeout: no duplication or corruption
- Partial failure at step N: recovery is explicit
- Worst material interleaving: invariants preserved

### Complete When
Retries, duplicates, and the worst material interleaving preserve stated invariants.

---

## External Integration

### Evidence Checklist
- [ ] Provider documentation version-matched to the version in use (not latest docs for an old SDK)
- [ ] Auth mechanism documented (API key, OAuth, mutual TLS)
- [ ] Rate limits, quotas, and throttling behavior documented
- [ ] Irreversible effects identified (charges, messages, notifications, remote writes)

### Key Decision Points
- What is the timeout budget? (Total request timeout, per-retry timeout, circuit breaker threshold)
- Which errors are retryable? (5xx yes, 4xx no, rate-limit with backoff)
- How are duplicate requests handled? (Idempotency key, deduplication window)
- What is the fallback when the provider is unavailable? (Queue and retry, degrade gracefully, fail hard)

### Common Traps
- **Retrying non-idempotent operations**: A payment charge that gets retried after a timeout can double-charge.
- **Using latest docs for old SDK**: The installed SDK version may not support features documented in the latest API version.
- **Missing circuit breaker**: Cascading failures when the provider goes down and every request waits for timeout.
- **No reconciliation**: After a timeout, the local state may not match the remote state. There must be a way to verify and correct.

### Minimum Verification
- Provider unavailable: timeout, retry, and fallback behavior tested
- Malformed response: handled without crash
- Rate-limited: backoff behavior tested
- Duplicate request: idempotency verified
- Partial remote success: local state reconciled

### Complete When
Dependency unavailability, malformed responses, throttling, duplicate requests, and partial remote success have explicit behavior.
