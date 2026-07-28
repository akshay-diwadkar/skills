# Investigate the Medium-Confidence Client Boundary
<!-- optimization-contract: 2; path: full; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Determine whether per-request client creation is a material cost.
- Success criteria: Preserve request behavior and promote only after timing and adapter compatibility are resolved.
- Constraints: No shared client state without lifecycle evidence.
- Exclusions: Quick Win classification from medium confidence.
- Protected behavior: Preserve request output, errors, authentication, and client lifecycle.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: current creates one client per request, but production timing and adapter metadata are unavailable.
- B-1: workflow: per-request client creation | method: blocked | command: collect production-equivalent construction timing | result: timings unavailable and safe confirmation is defined | confidence: medium | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: adapter compatibility must be resolved by the bounded experiment | target: B-1 | compatibility: unresolved

## Candidate Decisions
- C-1: band: investigate | impact: high | confidence: medium | effort: low | risk: medium | verification-strength: bounded | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=no, behavior=yes, compatibility=no, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: measure client construction and verify lifecycle compatibility | benefit: determine whether reuse is eligible | verify: V-1 | rollback: retain per-request creation | operational-cost: one disposable parity benchmark | experiment: resolve adapter metadata and compare construction plus request behavior
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: install a global shared client immediately | benefit: unspecified | verify: V-2 | rollback: restore per-request construction | operational-cost: shared lifecycle state | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Resolve adapter metadata, collect construction timing, test lifecycle parity, then reclassify.
- Behavior guardrails: Preserve authentication, output, errors, and lifecycle isolation.
- H-1: stage: plan | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run a disposable construction and request parity benchmark | expected: raw timing plus confirmed lifecycle compatibility.
- V-2: proves: C-2 | method: no accepted proof | expected: reject global client state.
- Rollback trigger: Any behavior mismatch or unresolved lifecycle constraint.
- Rollback action: Retain per-request client creation.
- Residual risk: Production connection behavior remains unknown.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: global reuse has no baseline or compatibility evidence | evidence: F-1, B-1 | revisit: prove safe lifecycle ownership.
- X-2: target: C-1 | status: deferred | reason: medium confidence cannot support promotion | evidence: F-1, B-1 | revisit: complete the named experiment.
