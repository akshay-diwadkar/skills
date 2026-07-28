# Improve CI Feedback Without Reducing Trust
<!-- optimization-contract: 2; path: full; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Reduce CI feedback latency while retaining trustworthy failures.
- Success criteria: Preserve coverage, type checking, release gates, and clear failures while reducing median CI duration below 5 minutes.
- Constraints: Keep every existing quality command.
- Exclusions: Skipping tests, type checks, or release gates.
- Protected behavior: Preserve coverage, type checking, release gates, failure visibility, and exit semantics.

## System and Coverage Map
- Subsystems: ci
- Passes: build-test-ci
- Sweep status: not-applicable
- CV-1: subsystem: ci | pass: build-test-ci | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `.github/workflows/ci.yml:4` | anchor: `python -m pytest` | observation: the quality job runs tests before mypy and owns the trusted feedback boundary.
- B-1: workflow: CI quality job | method: command | command: collect five representative quality-job runs | result: median 7 minutes across five CI runs | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: command-preserving CI ordering is local configuration | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: medium | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: .github/workflows/ci.yml:python -m pytest | change: run existing independent quality commands concurrently with unchanged failure reporting | benefit: reduce median CI duration below 5 minutes | verify: V-1 | rollback: restore sequential command ordering | operational-cost: bounded parallel runner usage | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | anchors: .github/workflows/ci.yml:python -m pytest | change: skip tests | benefit: shorter but untrusted feedback | verify: V-2 | rollback: restore required checks | operational-cost: lost defect detection | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Preserve both commands, isolate their logs, run them concurrently, and compare five representative jobs.
- Behavior guardrails: Preserve coverage, type checking, release gates, failure visibility, and exit semantics.
- H-1: stage: plan | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run both commands locally and compare five CI jobs | expected: identical checks and median below 5 minutes.
- V-2: proves: C-2 | method: inspect required gates | expected: reject skipping tests.
- Rollback trigger: Any missing check, hidden failure, or median at or above 5 minutes.
- Rollback action: Restore sequential command ordering.
- Residual risk: Runner contention may reduce the benefit.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: skipping tests destroys time-to-trust | evidence: F-1, B-1 | revisit: never without an equivalent trusted gate.
