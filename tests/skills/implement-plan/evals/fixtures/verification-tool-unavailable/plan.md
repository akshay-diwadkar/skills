# Enable the widget
<!-- plan-contract: 3 -->
<!-- tier: tiny; task-type: feature -->
<!-- plan-validation: 3; sha256: 9994a88757fb743a91446c6ae52f2bc9c278f1646ebc5068484701ef5e0bbe26 -->

## Outcome and Scope
- SC-1: Widget is enabled.
- In scope: `src/widget.py`.
- Unchanged: Widget identifier.

## Evidence Ledger
- F-1: `src/widget.py:1` | anchor: `ENABLED` | observation: Widget is disabled.

## Decisions
- D-1: selected: set flag | because: F-1 | rejected: runtime override.

## Implementation Specification
- CH-1: `src/widget.py` | anchor: `ENABLED` | status: existing | change: Set ENABLED to true.

## Traceability
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Restore flag hunk. |

## Verification
- T-1: given: widget module | expect: enabled | command: `widget-check src/widget.py`

## Risks, Assumptions, and Attack
- Assumptions: widget-check is installed.
- A1: not-applicable | evidence: Local flag.
- A2: not-applicable | evidence: No external effect.
- A6: repaired | evidence: Honest unavailable-tool handling.
