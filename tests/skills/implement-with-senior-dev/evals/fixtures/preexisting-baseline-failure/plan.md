# Return the feature name
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: feature -->
<!-- plan-validation: 3; sha256: 8a09ae9f59fa5d8325d88b22e934920898fad7da728d48e0df57f417a315df17 -->

## Outcome and Scope
- SC-1: `feature_name()` returns feature.
- In scope: `src/feature.py` and focused test.
- Unchanged: Existing unrelated failing test.

## Evidence Ledger
- F-1: `src/feature.py:1` | anchor: `feature_name` | observation: The function returns old.

## Decisions
- D-1: selected: change return value | because: F-1 | rejected: rename API.

## Implementation Specification
- CH-1: `src/feature.py` | anchor: `feature_name` | status: existing | change: Return feature.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Restore the return hunk. |

## Verification
- T-1: given: function call | expect: feature | command: `python -m pytest -q tests/test_feature.py`

## Risks, Assumptions, and Attack
- Assumptions: None.
- A1: not-applicable | evidence: Local API.
- A2: not-applicable | evidence: No external effect.
- A6: dismissed | evidence: Focused test.
