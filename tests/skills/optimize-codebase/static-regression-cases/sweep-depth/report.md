# Triage the Repository Sweep Before Deepening
<!-- optimization-contract: 2; path: full; scope: sweep; stage: plan -->

## Brief and Authorization
- Scope: sweep
- Stage: plan
- Authorization: plan-only
- Goal: Inventory application and CI optimization surfaces while deep-diving only the current high-signal runtime path.
- Success criteria: Account for every subsystem and pass, preserve behavior, and leave missing CI evidence resumable.
- Constraints: Deep-dive no more than one candidate in this wave.
- Exclusions: Speculative CI changes and unrelated application rewrites.
- Protected behavior: Preserve application output, CI coverage, release gates, and failure visibility.

## System and Coverage Map
- Subsystems: app, ci
- Passes: runtime, build-test-ci
- Sweep status: incomplete
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none
- CV-2: subsystem: app | pass: build-test-ci | status: clean | evidence: F-1 | priority: low | resume: none
- CV-3: subsystem: ci | pass: runtime | status: rejected | evidence: F-2 | priority: low | resume: none
- CV-4: subsystem: ci | pass: build-test-ci | status: deferred | evidence: F-2 | priority: high | resume: collect three representative CI timings

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: current is the only high-signal application runtime surface in this wave.
- F-2: `.github/workflows/ci.yml:4` | anchor: `python -m pytest` | observation: CI exists, but representative timing and cache evidence are unavailable.
- B-1: workflow: current transform loop | method: command | command: python bench.py | result: median 45 ms across five warm runs | confidence: high | evidence: F-1
- B-2: workflow: CI test job | method: blocked | command: collect three representative CI timings | result: representative CI timing unavailable and resume action defined | confidence: medium | evidence: F-2

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: selected runtime mechanism is local code | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: strategic-win | impact: high | confidence: high | effort: medium | risk: low | verification-strength: strong | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: consolidate repeated transformation setup at current | benefit: reduce the bounded runtime cost | verify: V-1 | rollback: restore the previous current implementation | operational-cost: bounded call-local state | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: optimize every surface in one wave | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: unbounded sweep depth | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Characterize current, change one boundary, compare the same workload, then resume CI evidence collection separately.
- Behavior guardrails: Preserve application behavior and every CI trust gate.
- H-1: stage: plan | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run parity tests and five warm benchmark runs | expected: identical behavior and a lower median.
- V-2: proves: C-2 | method: inspect the wave limit | expected: reject unbounded simultaneous deep-dives.
- Rollback trigger: Any behavior mismatch or neutral, worse, or inconclusive runtime result.
- Rollback action: Restore the previous current implementation.
- Residual risk: CI optimization remains unassessed until the deferred evidence is collected.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: it violates breadth-before-depth triage | evidence: F-1, B-1 | revisit: complete each bounded wave.
- X-2: target: CV-4 | status: deferred | reason: representative CI timing is unavailable in this wave | evidence: F-2 | revisit: collect three representative CI timings.
