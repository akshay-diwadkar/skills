# Consolidate the Measured User-Load Workflow
<!-- optimization-contract: 2; path: full; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Remove duplicated work across repeated user loads.
- Success criteria: Preserve output and reduce the five-run warm median below 20 ms.
- Constraints: No public behavior change.
- Exclusions: New dependencies and shared mutable caching.
- Protected behavior: Preserve output, errors, ordering, and side effects.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `load_users` | observation: load_users is the entry point for the repeated workflow.
- B-1: workflow: repeated user loads | method: command | command: python bench.py | result: median 48 ms across five warm runs | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: the mechanism is local code | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: strategic-win | impact: high | confidence: high | effort: medium | risk: low | verification-strength: strong | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:load_users | change: consolidate repeated workflow work at load_users | benefit: meet the 20 ms threshold | verify: V-1 | rollback: restore the previous workflow implementation | operational-cost: bounded request-local state | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:load_users | change: rewrite unrelated systems | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: broad migration | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Specify propagation from load_users, preserve observable ordering, then compare the identical workload.
- Behavior guardrails: Preserve output, errors, ordering, and effects.
- H-1: stage: plan | next: plan-change | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run parity tests and five warm benchmark runs | expected: identical behavior and median below 20 ms.
- V-2: proves: C-2 | method: no accepted proof | expected: reject the rewrite.
- Rollback trigger: Any behavior mismatch or median at or above 20 ms.
- Rollback action: Restore the previous workflow implementation.
- Residual risk: Production workload variance remains.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: unrelated rewrite lacks target evidence | evidence: F-1, B-1 | revisit: prove a separate bottleneck.
