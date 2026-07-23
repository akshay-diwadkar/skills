# Normalize missing names
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: bug-fix -->
<!-- plan-validation: 3; sha256: e39e97d5f124d7c155a283ace11a49a2e5f36f3eeb104abca27384a96bcf0eaf -->

## Outcome and Scope
- SC-1: `normalize_name(None)` returns an empty string.
- In scope: `src/names.py` and its focused test.
- Unchanged: Non-null strings remain stripped.

## Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: The current function calls strip unconditionally.

## Decisions
- D-1: selected: guard None before strip | because: F-1 | rejected: widen the return type.

## Implementation Specification
- CH-1: `src/names.py` | anchor: `normalize_name` | status: existing | change: Return an empty string for None; otherwise return the stripped input.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Restore the recorded function hunk. |

## Verification
- T-1: given: None and padded text | expect: empty string and stripped text | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: None.
- A1: not-applicable | evidence: Local return guard.
- A2: not-applicable | evidence: No external effect.
- A6: dismissed | evidence: T-1 covers both branches.
