"""Legacy parser inputs kept out of user-facing plan-change references."""

TINY = """# Handle Missing Names
<!-- tier: tiny; task-type: bug-fix -->
<!-- plan-validation: 3; sha256: 0000000000000000000000000000000000000000000000000000000000000000 -->

## Outcome and Scope
- SC-1: normalize missing names without changing valid strings.
## Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: input permits None.
- F-2: `src/names.py:2` | anchor: `strip` | observation: input is dereferenced.
## Decisions
- D-1: selected: return empty string | because: callers need strings | rejected: return None.
## Implementation Specification
- CH-1: `src/names.py` | anchor: `normalize_name` | status: existing | change: guard None before stripping.
- CH-2: `tests/test_names.py` | anchor: `test_missing_name` | status: new | change: cover null and valid strings.
## Traceability
| Criterion | Changes | Tests |
|---|---|---|
| SC-1 | CH-1, CH-2 | T-1 |
## Verification
- T-1: given: None and a valid string | expect: empty and normalized strings | command: `pytest`.
## Risks
- R-1 P2: local behavior change.
"""

STANDARD = """# Scope cached flags
## Outcome and Scope
- SC-1: cache entries include tenant identity.
## Evidence Ledger
- F-1: `src/flags.py:1` | anchor: `_cache` | observation: cache is shared.
## Decisions
- D-1: selected: use a tuple key | because: tenant and user identify the value | rejected: clear cache.
## Implementation Specification
- CH-1: `src/flags.py` | anchor: `flags_for` | status: existing | change: use a tenant and user key.
- CH-2: `tests/test_flags.py` | anchor: `test_scoped_cache` | status: new | change: cover two tenants.
### Execution Blueprint: CH-1 - tenant cache flow
~~~pseudocode
key = (tenant_id, user_id)
return cache[key]
~~~
## Traceability
| Criterion | Changes | Tests |
|---|---|---|
| SC-1 | CH-1, CH-2 | T-1 |
## Verification
- T-1: given: two tenants and one user | expect: separate flags | command: `pytest`.
"""

HIGH_RISK = """# Add tenant identity
## Outcome and Scope
- SC-1: events carry tenant identity compatibly.
## Evidence Ledger
- F-1: `src/schema.py:4` | anchor: `UserEvent` | observation: event has one field.
## Decisions
- D-1: selected: optional field | because: old readers exist | rejected: required field.
## Implementation Specification
- CH-1: `src/schema.py` | anchor: `UserEvent` | status: existing | change: add optional tenant identity.
### Execution Blueprint: CH-1 - event shape
~~~python
tenant_id: str | None
~~~
## Traceability
| Criterion | Changes | Tests |
|---|---|---|
| SC-1 | CH-1 | T-1 |
## Verification
- T-1: given: old and new events | expect: both read | command: `pytest`.
## Risks
- R-1 P1: missing tenant identity. Resolution: CH-1 T-1.
"""
