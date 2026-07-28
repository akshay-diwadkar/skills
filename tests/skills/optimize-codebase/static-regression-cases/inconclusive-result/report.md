# Roll Back the Inconclusive Optimization
<!-- optimization-contract: 2; path: full; scope: targeted; stage: implementation -->

## Brief and Authorization
- Scope: targeted
- Stage: implementation
- Authorization: explicit implementation — user authorized one validated local optimization
- Goal: Reduce local normalization runtime without changing behavior.
- Success criteria: Preserve behavior and improve the five-run median below 40 ms.
- Constraints: Apply only C-1 and use the identical benchmark workload.
- Exclusions: Unrelated changes and success claims without improvement.
- Protected behavior: Preserve normalized output, ordering, errors, and side effects.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: current owns the bounded normalization workflow.
- B-1: workflow: current normalization | method: command | command: python bench.py before | result: median 40 ms across five warm runs | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: local change needs no ecosystem capability | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: medium | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: consolidate the local normalization pass | benefit: improve the median below 40 ms | verify: V-1 | rollback: restore the previous current body | operational-cost: none | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: rewrite unrelated normalization systems | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: broad migration | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Apply C-1, run parity checks, compare the identical workload, and roll back on a neutral or worse result.
- Behavior guardrails: Preserve output, ordering, errors, and side effects.
- H-1: stage: implementation | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run parity tests and the identical five-run benchmark | expected: identical behavior and median below 40 ms.
- V-2: proves: C-2 | method: no accepted proof | expected: reject the unrelated rewrite.
- Rollback trigger: Any behavior mismatch or median at or above 40 ms.
- Rollback action: Restore the previous current body and rerun parity tests.
- Residual risk: The measured result may vary across production workloads.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: broad rewrite is outside the authorized candidate | evidence: F-1, B-1 | revisit: prove a separate bottleneck.

## Execution Record
- E-1: candidate: C-1 | authorization: user authorized candidate C-1 | change: applied the local normalization optimization then restored it | result: parity passed but the 42 ms median is inconclusive; rollback selected | regression: V-1

## Before/After Verification
- B-2: workflow: current normalization | method: command | command: python bench.py after | result: median 42 ms across five warm runs | confidence: high | evidence: F-1
- Comparison: B-1 -> B-2 used the same workload, runtime, cache state, and five-run median; the result was worse.
