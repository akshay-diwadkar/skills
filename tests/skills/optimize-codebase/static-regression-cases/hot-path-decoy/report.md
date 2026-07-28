# Prefer the Verified Hot Path Over the Cache Decoy
<!-- optimization-contract: 2; path: full; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Reduce repeated fetch work on the verified hot path.
- Success criteria: Preserve output and reduce the five-run warm median below 25 ms.
- Constraints: No new dependency and no public behavior change.
- Exclusions: Shared caching and unrelated rewrites.
- Protected behavior: Preserve output, fetch ordering, errors, and side effects.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: current owns the repeated store fetch hot path; package.json is an ungrounded cache decoy.
- B-1: workflow: current fetch loop | method: command | command: python bench.py | result: median 40 ms across five warm runs | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: the selected mechanism is local code and does not use the cache package | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: medium | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: remove repeated call-local work inside current | benefit: meet the 25 ms threshold | verify: V-1 | rollback: restore the previous current body | operational-cost: bounded call-local memory | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: add shared caching | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: shared state and invalidation | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Characterize current, change its local implementation, run parity tests, and repeat the warm benchmark.
- Behavior guardrails: Preserve exact output, fetch ordering, errors, and side effects.
- H-1: stage: plan | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run parity tests and five warm benchmark runs | expected: identical behavior and median below 25 ms.
- V-2: proves: C-2 | method: no accepted proof | expected: reject shared caching.
- Rollback trigger: Any behavior mismatch or median at or above 25 ms.
- Rollback action: Restore the previous current body and rerun parity tests.
- Residual risk: Production workload variance remains.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: shared-cache semantics are outside the request and unsupported by hot-path evidence | evidence: F-1, B-1 | revisit: define freshness and prove cross-call reuse.
