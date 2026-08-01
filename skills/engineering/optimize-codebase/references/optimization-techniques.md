# Optimization Techniques

Read this file only after the contract selects the matching branch. Keep local
evidence primary and record the source and version of every external claim.

## Research and ecosystem

Use documentation research to confirm a versioned capability, constraint, or
support window that could change the selected mechanism. Prefer official
documentation and record compatibility, migration cost, and operational
tradeoffs. Do not turn a current release or popular pattern into a candidate
without a local target and baseline.

## Pattern probes

Probe the narrowest leverage point first: remove duplicate work, reduce
serialization or I/O, bound retries, improve locality, or make a build/CI
critical path observable. Compare a small local change with one structurally
different option. For each option, state expected behavior, measurement,
compatibility impact, blast radius, rollback, and what evidence would disconfirm
it.

## Handoff calibration

Use examples only to calibrate record shape. Keep one candidate per report,
explicitly account for every requested sweep pair, and make deferred work
resumable. If a fast-path patch regresses or is neutral, worse, or inconclusive,
revert only that introduced patch and return to the full path.
