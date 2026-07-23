# Parse integer input completely
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: bug-fix -->
<!-- plan-validation: 3; sha256: 5285fa3c1faad3cb54c38a9170be3384182661f908dd4c0ff6d4dc94c05f26e2 -->

## Outcome and Scope
- SC-1: Parser handles valid, empty, and invalid input exactly.
- In scope: `src/parser.py` and tests.
- Unchanged: Integer output for valid values.

## Evidence Ledger
- F-1: `src/parser.py:1` | anchor: `parse_value` | observation: Parser handles only valid input.

## Decisions
- D-1: selected: explicit branches | because: F-1 | rejected: silent coercion.

## Implementation Specification
- CH-1: `src/parser.py` | anchor: `parse_value` | status: existing | change: Return zero for empty input, parse valid integers, and raise ValueError with invalid value for non-integers.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Restore parser hunk. |

## Verification
- T-1: given: 4, empty, and x | expect: 4, zero, and ValueError invalid value | command: `python -m pytest -q`

## Risks, Assumptions, and Attack
- Assumptions: ASCII inputs.
- A1: not-applicable | evidence: Local parser.
- A2: not-applicable | evidence: No external effect.
- A6: repaired | evidence: Three branch tests.
