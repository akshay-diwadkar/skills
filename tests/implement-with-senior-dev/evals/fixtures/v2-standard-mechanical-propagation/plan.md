# Add explicit locale formatting
<!-- plan-contract: 2 -->
<!-- tier: standard; task-type: feature -->

## Outcome and Scope
- SC-1: Formatting uses an explicit locale.
- In scope: `src/api.py`, focused tests, and deterministic compatibility propagation.
- Unchanged: The formatted value remains identical for the default locale.

## Evidence Ledger
- F-1: `src/api.py:1` | anchor: `format_name` | observation: Formatting currently has no locale parameter.

## Decisions
- D-1: selected: require locale internally | because: F-1 | rejected: global configuration.

## Implementation Specification
- CH-1: `src/api.py` | anchor: `format_name` | status: existing | change: Add a required locale parameter and preserve output when locale is en.

## Traceability
- C-1: Existing output stays stable | status: preserved
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Restore the recorded interface hunk. |
| C-1 | CH-1 | T-1 | Verify existing output. |

## Verification
- T-1: given: Ada and en | expect: Ada | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: Existing internal callers use en.
- A1: repaired | evidence: Type-check/test reveals deterministic caller propagation.
- A2: not-applicable | evidence: No external effect.
- A3: not-applicable | evidence: Pure formatting.
- A4: not-applicable | evidence: No shared state.
- A5: not-applicable | evidence: No migration.
- A6: dismissed | evidence: T-1 covers compatibility.
