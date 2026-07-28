# Route the Optimization as Plan-Only
<!-- optimization-contract: 2; path: full; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Plan a local normalization improvement without repository mutation.
- Success criteria: Preserve normalized output and provide a decision-complete local plan.
- Constraints: No edits or execution records in this run.
- Exclusions: Implementation and unrelated refactors.
- Protected behavior: Preserve output, ordering, errors, and side effects.

## System and Coverage Map
- Subsystems: app
- Passes: maintainability
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: maintainability | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: current is the only local normalization owner.
- B-1: workflow: item normalization | method: static | command: inspect current and its bounded return path | result: one function and one list transformation | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: local plan needs no ecosystem capability | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: medium | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: consolidate the local normalization traversal | benefit: retain one bounded transformation | verify: V-1 | rollback: restore the previous current body | operational-cost: none | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: rewrite unrelated normalization callers | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: broad migration | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Characterize output, change current only after separate authorization, then run focused parity tests.
- Behavior guardrails: Preserve ordering, output, errors, and side effects.
- H-1: stage: plan | next: implement-plan | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run focused normalization parity tests | expected: identical ordered values and errors.
- V-2: proves: C-2 | method: no accepted proof | expected: reject the broad rewrite.
- Rollback trigger: Any output, ordering, or error mismatch.
- Rollback action: Restore the previous current body.
- Residual risk: Input-size variance remains.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: cross-module rewrite is outside the authorized plan scope | evidence: F-1, B-1 | revisit: prove a broader ownership problem.
