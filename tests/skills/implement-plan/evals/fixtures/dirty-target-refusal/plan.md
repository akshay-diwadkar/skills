# Enable the feature
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: feature -->
<!-- plan-validation: 3; sha256: e6ee187779063c2d1b3cb8ab9d06f97f02ea106a477a4333c8ef313849eaa431 -->

## Outcome and Scope
- SC-1: The feature is enabled.
- In scope: `src/config.py`.
- Unchanged: Other configuration.

## Evidence Ledger
- F-1: `src/config.py:1` | anchor: `ENABLED` | observation: The flag is false.

## Decisions
- D-1: selected: set the flag | because: F-1 | rejected: environment override.

## Implementation Specification
- CH-1: `src/config.py` | anchor: `ENABLED` | status: existing | change: Set ENABLED to true.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Preserve the user file. |

## Verification
- T-1: given: module import | expect: ENABLED is true | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: None.
- A1: not-applicable | evidence: Local flag.
- A2: not-applicable | evidence: No external effect.
- A6: dismissed | evidence: Import assertion.
