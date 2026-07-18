# Update the missing handler
<!-- plan-contract: 2 -->
<!-- tier: tiny; task-type: bug-fix -->

## Outcome and Scope
- SC-1: The missing handler returns ok.
- In scope: `src/service.py`.
- Unchanged: Other service behavior.

## Evidence Ledger
- F-1: `src/service.py:1` | anchor: `missing_handler` | observation: The planned handler exists.

## Decisions
- D-1: selected: update handler | because: F-1 | rejected: add a second handler.

## Implementation Specification
- CH-1: `src/service.py` | anchor: `missing_handler` | status: existing | change: Return ok.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Preserve the file. |

## Verification
- T-1: given: handler call | expect: ok | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: None.
- A1: not-applicable | evidence: Local change.
- A2: not-applicable | evidence: No external effect.
- A6: dismissed | evidence: Focused test.
