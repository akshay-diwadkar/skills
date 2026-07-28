# Consolidate the Duplicated Policy
<!-- optimization-contract: 2; path: full; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Improve maintainability by consolidating duplicated normalization policy.
- Success criteria: Preserve every return value while reducing three policy branches to one bounded owner.
- Constraints: Use bounded static evidence and make no timing claim.
- Exclusions: Performance percentages and unrelated refactors.
- Protected behavior: Preserve returned values, branch behavior, and errors.

## System and Coverage Map
- Subsystems: app
- Passes: maintainability
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: maintainability | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: current contains the complete duplicated policy boundary.
- B-1: workflow: normalization policy | method: static | command: inspect every return path in current | result: three duplicated policy branches across one bounded change path | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: local maintainability change needs no ecosystem capability | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: medium | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: consolidate duplicated normalization policy inside current | benefit: reduce three policy branches to one maintainability owner | verify: V-1 | rollback: restore the explicit branches | operational-cost: none | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: rewrite the policy subsystem | benefit: unspecified | verify: V-2 | rollback: restore the repository | operational-cost: broad migration | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Characterize all three branches, consolidate the local policy, and run branch parity tests.
- Behavior guardrails: Preserve exact returned values and error behavior.
- H-1: stage: plan | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run focused tests for a, b, and fallback values | expected: identical output with one policy owner.
- V-2: proves: C-2 | method: no accepted proof | expected: reject the broad rewrite.
- Rollback trigger: Any branch output or error mismatch.
- Rollback action: Restore the explicit policy branches.
- Residual risk: Future branches may require new explicit policy.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: broad rewrite has no bounded static evidence | evidence: F-1, B-1 | revisit: prove cross-module duplication.
