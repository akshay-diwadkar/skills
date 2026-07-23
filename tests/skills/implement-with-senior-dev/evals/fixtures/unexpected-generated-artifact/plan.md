# Rename the model field
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: refactor -->
<!-- plan-validation: 3; sha256: 638c16cd75a33608ca73d05b24324598f776681b5edefc44c9d6e549fc42761e -->

## Outcome and Scope
- SC-1: Internal model uses display_name.
- In scope: `src/model.py` only.
- Unchanged: Generated public schema.

## Evidence Ledger
- F-1: `src/model.py:1` | anchor: `name` | observation: Model uses name.

## Decisions
- D-1: selected: local rename | because: F-1 | rejected: public schema change.

## Implementation Specification
- CH-1: `src/model.py` | anchor: `name` | status: existing | change: Rename internal field to display_name.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Preserve schema output. |

## Verification
- T-1: given: generator check | expect: no schema change | command: `python generate.py`

## Risks, Assumptions, and Attack
- Assumptions: Generator is stable.
- A1: repaired | evidence: Generated surface inspected.
- A2: not-applicable | evidence: Local files.
- A6: repaired | evidence: Generated diff gate.
