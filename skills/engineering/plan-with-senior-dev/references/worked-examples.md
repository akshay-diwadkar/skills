# Worked Examples

Read only the matching tier. Each fenced plan validates against the corresponding repository under `tests/skills/plan-with-senior-dev/fixtures/`.

## Tiny

```plan
# Handle Missing Names Without Changing Valid Normalization
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: bug-fix -->
<!-- plan-validation: 3; sha256: 3933df7dc8bcd875b979062331d7323a3fe9bd41b092fb490d637c4810158d50 -->

## Outcome and Scope
- SC-1: `normalize_name(None)` returns `""`; non-null strings retain strip-and-lower behavior.
- In scope: the null branch and focused regression coverage.
- Unchanged: non-null input normalization and the `str` return type.

## Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: The declared input is nullable and the return type is `str`.
- F-2: `src/names.py:2` | anchor: `strip` | observation: The implementation dereferences the nullable input without a guard.

## Decisions
- D-1: selected: return an empty string for `None` before normalization | because: the request preserves a non-null `str` result | rejected: return `None`, which widens the return contract and callers.

## Implementation Specification
- CH-1: `src/names.py` | anchor: `normalize_name` | status: existing | change: if `name is None`, return `""`; otherwise return `name.strip().lower()` unchanged.
- CH-2: `tests/test_names.py` | anchor: `test_returns_empty_string_for_missing_name` | status: new | change: add exact null and existing valid-string regression assertions.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1, CH-2 | T-1 | Revert both files; no durable state |

## Verification
- T-1: given: `None`, `"  Alice  "`, and `""` | expect: `""`, `"alice"`, and `""` respectively | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: None.
- A1: dismissed | evidence: CH-1 preserves the return type and non-null behavior, so existing callers require no update.
- A2: repaired | evidence: CH-1 and T-1 specify null, empty, and whitespace-bearing input behavior.
- A6: dismissed | evidence: CH-1 supplies both branches and CH-2 supplies exact assertions.
```

## Standard

```plan
# Isolate Cached Feature Flags by Tenant and User
<!-- plan-contract: 3 -->
<!-- tier: standard; task-type: bug-fix -->
<!-- plan-validation: 3; sha256: 3ee1a884be29e3a532a96b5825fc9dda8058536d5ebe4753228b6e2b9864defa -->

## Outcome and Scope
- SC-1: Two tenants using the same user ID receive only their own tenant-scoped flags.
- In scope: cache identity and cross-tenant regression coverage.
- Unchanged: `flags_for` parameters, return type, and flag loading format.

## Evidence Ledger
- F-1: `src/flags.py:1` | anchor: `_cache` | observation: The module stores feature flags in shared process state.
- F-2: `src/flags.py:8` | anchor: `flags_for` | observation: The lookup receives both tenant and user identity.
- F-3: `src/flags.py:9` | anchor: `user_id` | observation: The cache check uses only user identity.

## Decisions
- D-1: selected: key the cache by `(tenant_id, user_id)` | because: both identities already reach `flags_for` and define the loaded value | rejected: clear the cache between tenants, which hides the missing identity and remains order-dependent.

## Implementation Specification
- CH-1: `src/flags.py` | anchor: `_cache` | status: existing | change: type the cache as `dict[tuple[str, str], list[str]]`; construct `key = (tenant_id, user_id)` and use it for lookup, assignment, and return.
- CH-2: `tests/test_flags.py` | anchor: `test_isolates_same_user_id_across_tenants` | status: new | change: call the function for two tenants sharing one user ID and assert distinct exact lists.

### Execution Blueprint: CH-1 — Tenant-scoped cache flow
~~~pseudocode
flags_for(tenant_id: str, user_id: str) -> list[str]:
    key = (tenant_id, user_id)
    if key exists in _cache:
        return _cache[key]
    flags = load_flags(tenant_id, user_id)
    _cache[key] = flags
    return flags
~~~

## Traceability
- C-1: Tenant identity participates in every cache read and write | status: modified
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1, CH-2 | T-1 | Modified cache identity; process restart or revert clears ephemeral state |
| C-1 | CH-1 | T-1 | Preserved after tuple-key change |

## Verification
- T-1: given: tenant `acme` and tenant `globex` with user `u1` | expect: `["acme:u1:enabled"]` and `["globex:u1:enabled"]` | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: Low-impact and reversible: the cache is process-local, as shown by F-1.
- A1: dismissed | evidence: CH-1 does not change the `flags_for` signature or return type.
- A2: dismissed | evidence: CH-1 preserves existing string inputs and exact output construction.
- A3: dismissed | evidence: duplicate concurrent loads assign the same deterministic value and create no durable effect in the fixture.
- A4: dismissed | evidence: the cache is ephemeral and a restart or revert removes tuple-key entries.
- A5: dismissed | evidence: CH-1 keeps one dictionary lookup and one load per cache miss.
- A6: dismissed | evidence: CH-1 names every changed cache operation and T-1 names exact inputs and outputs.
```

## High-Risk

```plan
# Add Tenant Identity to User Events Compatibly
<!-- plan-contract: 3 -->
<!-- tier: high-risk; task-type: public-contract -->
<!-- plan-validation: 3; sha256: 42b9a8812c21b8cf2e0799542dde5dbe82ba4d3d730b8e4c52ff8c67d4877a09 -->

## Outcome and Scope
- SC-1: New events carry a non-empty tenant ID while old events remain readable as tenant `unknown`.
- SC-2: Existing producer callers that omit tenant identity continue producing the old one-field event.
- In scope: event type, producer shape, validation, compatibility tests, and rollout order.
- Unchanged: `user_id` spelling and type; consumers may continue ignoring unknown keys.

## Evidence Ledger
- F-1: `src/schema.py:4` | anchor: `UserEvent` | observation: The shared event contract is a `TypedDict`.
- F-2: `src/schema.py:5` | anchor: `user_id` | observation: The current contract contains only required `user_id`.
- F-3: `src/producer.py:4` | anchor: `build_event` | observation: Existing producer callers provide only user identity.
- F-4: `src/consumer.py:5` | anchor: `tenant_id` | observation: The consumer already maps a missing tenant field to `unknown`.

## Decisions
- D-1: selected: add `tenant_id` as `NotRequired[str]` and make the producer parameter optional | because: F-4 proves old events have an explicit read fallback | rejected: make the field required immediately, which breaks old producers and stored events.

## Implementation Specification
- CH-1: `src/schema.py` | anchor: `UserEvent` | status: existing | change: import `NotRequired`, then add `tenant_id: NotRequired[str]` while preserving required `user_id`.
- CH-2: `src/producer.py` | anchor: `build_event` | status: existing | change: add `tenant_id: str | None = None`; omit the key for `None`, raise `ValueError("tenant_id must not be empty")` for `""`, and include the key otherwise.
- CH-3: `tests/test_events.py` | anchor: `test_old_and_new_event_versions_are_compatible` | status: new | change: cover old producer calls, new tenant events, empty tenant rejection, and consumer reads of old/new shapes.

### Execution Blueprint: CH-1, CH-2 — Complete event shapes and compatibility
~~~python
# Before
class UserEvent(TypedDict):
    user_id: str

def build_event(user_id: str) -> UserEvent: ...

# After
class UserEvent(TypedDict):
    user_id: str
    tenant_id: NotRequired[str]

def build_event(user_id: str, tenant_id: str | None = None) -> UserEvent: ...
~~~

| Writer / reader | Old reader | New reader |
|---|---|---|
| Old writer: `{user_id}` | Reads `user_id` | Reads tenant as `unknown` |
| New writer: `{user_id, tenant_id}` | Ignores additive key | Reads exact tenant |

## Traceability
- C-1: Old event readers and writers remain compatible during mixed-version rollout | status: at-risk
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1, CH-2, CH-3 | T-1, T-2 | Additive optional field; disable new argument to roll back |
| SC-2 | CH-2, CH-3 | T-1 | Optional default preserves old calls |
| C-1 | CH-1, CH-2 | T-1 | Consumer-first rollout and omission default preserve compatibility |

## Verification
- T-1: given: old call `build_event("u1")` and new call `build_event("u1", "acme")` | expect: `{"user_id": "u1"}` and `{"user_id": "u1", "tenant_id": "acme"}`; consumer returns `unknown` and `acme` | command: `python -m pytest -q`
- T-2: given: `build_event("u1", "")` | expect: `ValueError("tenant_id must not be empty")` | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: None.
- R-1 P1: A blank tenant ID becomes indistinguishable from missing identity | Resolution: CH-2/T-2
- A1: repaired | evidence: CH-3 covers the existing producer call and the consumer fallback.
- A2: repaired | evidence: CH-2 and T-2 specify `None`, empty, and non-empty tenant behavior.
- A3: not-applicable | evidence: the change constructs immutable event values and touches no shared mutable state.
- A4: repaired | evidence: tenant identity is optional and rollback stops passing it without rewriting stored events.
- A5: dismissed | evidence: the change adds one constant-time validation and dictionary field.
- A6: dismissed | evidence: CH-1 and CH-2 specify complete types, defaults, branches, and errors.

## Compatibility and Rollout
Deployment order is new consumer behavior first, then the schema and producer. Old readers ignore the new dictionary key; new readers return `unknown` for old events. Monitor empty-tenant validation failures and the fraction of events without tenant identity. Stop rollout if validation failures exceed the existing error baseline or any consumer rejects the additive key.

## Durable Rollback
Code rollback stops producers from supplying tenant identity. Existing data remains readable because the field is optional; queued old and new events are both accepted. No cache format changes exist. No irreversible external effect is introduced.
```
