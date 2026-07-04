# Constraint Propagation Protocol

Use this whenever behavior, contracts, data, security, performance, compatibility, or business rules can be affected.

## Step 1: Enumerate

List every relevant constraint in the affected area:

- Type signatures and interface contracts.
- Data validation rules, schemas, serialization, nullability, and state transitions.
- Performance SLAs, hot-path complexity, pagination, batching, and memory limits.
- Security invariants: auth, permissions, input validation, tenant boundaries, secrets.
- API backward compatibility guarantees and client contracts.
- Test assertions, fixtures, or snapshots that encode expected behavior.
- Business rules, domain terms, legal or regulatory requirements.

## Step 2: Classify

For each constraint, classify it:

- Preserved: the plan does not affect the constraint. Cite evidence.
- Modified: the plan intentionally changes the constraint. Document old value, new value, and migration path.
- At risk: the plan might accidentally violate the constraint. Add verification and rollback considerations.

## Step 3: Verify

For every At risk constraint:

- Add an explicit verification step to the plan.
- Add a test assertion to the test strategy.
- Add rollback detail if violation would be destructive, public, or hard to reverse.

## Output Format

Use a table in Standard and High-risk plans:

```markdown
## Constraint Verification

| Constraint | Current value / evidence | Classification | Plan preserves? |
|---|---|---|---|
| API response shape | `src/api/orders.ts:42` returns `{ id, status }` | Preserved | Yes - no response fields change |
| Retry limit | `src/jobs/retry.ts:18` uses 3 attempts | At risk | Verify with retry test before merge |
```

If any At risk constraint lacks a verification step, the plan is incomplete.
