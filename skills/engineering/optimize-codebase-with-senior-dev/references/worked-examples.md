# Worked Optimization Examples

Read only the example matching the current branch. Each fenced report validates against the same-named fixture under `tests/optimize-codebase-with-senior-dev/evals/fixtures/`.

## Measured Targeted Runtime Optimization

<!-- example: measured-runtime -->

```optimization
# Batch Repeated User Loads
<!-- optimization-contract: 1; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Reduce store calls in the user-loading workflow while preserving ordered results.
- Protected behavior: Preserve the function signature, result order, missing-user errors, and read-only behavior.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `load_users` | observation: The workflow loads users through one cohesive function.
- B-1: workflow: load 100 users | method: command | command: python bench.py | result: median 101 store calls across 5 warm runs | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: The candidate is a local batching change with no ecosystem claim | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: high | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | change: replace repeated fetches with the store's existing bulk read while restoring input order | benefit: reduce 101 store calls to at most 2 for 100 users | verify: V-1 | rollback: restore the previous list-comprehension implementation | operational-cost: one bounded result map with no new service or dependency | experiment: none
- C-2: band: rejected | impact: medium | confidence: low | effort: medium | risk: medium | verification-strength: missing | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=no, compatibility=yes, verification=no, rollback=yes, operational-cost=no, decisions=yes | evidence: F-1, B-1, R-1 | change: add a shared process cache | benefit: avoid repeated reads across calls | verify: V-2 | rollback: disable and remove the cache | operational-cost: unbounded freshness and memory ownership | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Update the existing store adapter call, restore input ordering locally, then add focused call-count and behavior tests.
- Behavior guardrails: Preserve duplicates, input order, errors, and the public return type.
- H-1: stage: plan | next: plan-with-senior-dev | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run focused behavior tests and five warm benchmark runs | expected: identical ordered results and no more than 2 store calls for 100 users.
- V-2: proves: C-2 | method: no safe proof accepted | expected: rejected because freshness semantics are undefined.
- Rollback trigger: Any result-order, duplicate, or error-contract mismatch, or median calls above 2.
- Rollback action: Restore the previous list comprehension and rerun focused tests.
- Residual risk: Bulk-read limits may require chunking above the benchmark size; keep the existing maximum request size.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: A cache changes freshness and ownership without evidence that cross-call reads dominate | evidence: F-1, B-1 | revisit: profile repeated cross-call reads and define invalidation semantics.
```

## Sweep With Explicit Deferral

<!-- example: sweep-depth -->

```optimization
# Prioritize One Sweep Wave
<!-- optimization-contract: 1; scope: sweep; stage: plan -->

## Brief and Authorization
- Scope: sweep
- Stage: plan
- Authorization: plan-only
- Goal: Map application and CI optimization surfaces without silently sampling the repository.
- Protected behavior: Preserve runtime output, test coverage, failure visibility, and release gates.

## System and Coverage Map
- Subsystems: app, ci
- Passes: runtime, build-test-ci
- Sweep status: incomplete
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none
- CV-2: subsystem: app | pass: build-test-ci | status: clean | evidence: F-1 | priority: low | resume: none
- CV-3: subsystem: ci | pass: runtime | status: rejected | evidence: F-1 | priority: low | resume: none
- CV-4: subsystem: ci | pass: build-test-ci | status: deferred | evidence: F-1 | priority: high | resume: collect three CI timing exports and cache-hit metadata in the next wave

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `current` | observation: The application owns one serial item-processing path; CI evidence is not present in the fixture.
- B-1: workflow: process 1000 items | method: static | command: inspect process_items | result: one independent transform call per item with no external I/O | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: This wave evaluates a local processing boundary before ecosystem research | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: strategic-win | impact: high | confidence: high | effort: medium | risk: low | verification-strength: bounded | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | change: introduce the existing batch transform at the app boundary while preserving ordered output | benefit: remove per-item orchestration overhead on the measured path | verify: V-1 | rollback: restore the serial transform loop | operational-cost: bounded batch memory sized to the existing request limit | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: high | risk: high | verification-strength: missing | blast-radius: high | reversible: no | independent: no | gates: target=no, baseline=no, behavior=no, compatibility=no, verification=no, rollback=no, operational-cost=no, decisions=no | evidence: F-1, B-1, R-1 | change: rewrite application and CI orchestration together | benefit: unspecified modernization | verify: V-2 | rollback: restore the current repository from version control | operational-cost: broad migration and ownership growth | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Characterize ordering, add a batch-path test, change one app boundary, and compare the same workload.
- Behavior guardrails: Do not change CI, coverage, output order, errors, or release behavior in this wave.
- H-1: stage: plan | next: plan-with-senior-dev | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run identical 1000-item inputs through serial and batch paths | expected: byte-identical ordered results with lower median orchestration time.
- V-2: proves: C-2 | method: no bounded verification exists | expected: reject the unrelated rewrite.
- Rollback trigger: Any output mismatch or neutral/worse median under the same workload.
- Rollback action: Restore the serial loop and retain the characterization test.
- Residual risk: CI optimization remains unassessed until timing and cache evidence are available.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: The rewrite has no target, baseline, or reversible boundary | evidence: F-1 | revisit: never without a separate evidenced goal.
- X-2: target: CV-4 | status: deferred | reason: CI timing and cache-hit evidence are unavailable in this wave | evidence: F-1 | revisit: resume after collecting three representative CI runs.
```

## Medium-Confidence Investigation

<!-- example: investigate-compatibility -->

```optimization
# Confirm Pooling Support Before Recommending It
<!-- optimization-contract: 1; scope: targeted; stage: plan -->

## Brief and Authorization
- Scope: targeted
- Stage: plan
- Authorization: plan-only
- Goal: Determine whether connection reuse can reduce request setup time.
- Protected behavior: Preserve authentication, timeout, retry, cancellation, and error contracts.

## System and Coverage Map
- Subsystems: api
- Passes: backend-api
- Sweep status: not-applicable
- CV-1: subsystem: api | pass: backend-api | status: candidate | evidence: F-1 | priority: medium | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `client_for_request` | observation: A client is constructed on the request path, but production timing and resolved adapter metadata are unavailable.
- B-1: workflow: create request client | method: blocked | command: production trace unavailable | result: client construction is reachable but its latency share is unknown | confidence: medium | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: Version-matched pooling research is deferred until installed adapter metadata is available | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: investigate | impact: high | confidence: medium | effort: low | risk: medium | verification-strength: bounded | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=no, behavior=yes, compatibility=no, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | change: evaluate a shared supported client with bounded connection pooling | benefit: potentially remove per-request setup latency | verify: V-1 | rollback: retain per-request construction until the experiment passes | operational-cost: bounded idle connections and lifecycle ownership | experiment: resolve the installed adapter version, capture request setup traces, and run a 100-request parity benchmark in a disposable environment

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Resolve adapter metadata, read matching official pooling documentation, capture baseline traces, then decide whether promotion gates pass.
- Behavior guardrails: Do not edit request lifecycle code or recommend pooling before compatibility and latency evidence exist.
- H-1: stage: plan | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: compare 100 requests with lifecycle, auth, timeout, and error parity | expected: promote only if setup latency materially falls and all behavior checks match.
- Rollback trigger: Any lifecycle mismatch, connection leak, or unmeasured latency benefit.
- Rollback action: Keep per-request client construction unchanged.
- Residual risk: Production concurrency may differ from the disposable experiment and requires a bounded rollout if promoted.

## Rejects, Deferrals, and Limitations
- X-1: target: C-1 | status: deferred | reason: Baseline and resolved-version compatibility evidence are missing | evidence: F-1, B-1 | revisit: complete the named experiment and version-matched research.
```

## Explicitly Authorized Implementation

<!-- example: authorized-implementation -->

```optimization
# Apply One Validated Local Optimization
<!-- optimization-contract: 1; scope: targeted; stage: implementation -->

## Brief and Authorization
- Scope: targeted
- Stage: implementation
- Authorization: explicit implementation — user requested the validated local batching candidate
- Goal: Reduce repeated normalization work without changing output.
- Protected behavior: Preserve the public function, ordered values, exceptions, and side effects.

## System and Coverage Map
- Subsystems: app
- Passes: runtime
- Sweep status: not-applicable
- CV-1: subsystem: app | pass: runtime | status: candidate | evidence: F-1 | priority: high | resume: none

## Evidence and Baselines
- F-1: `src/system.py:1` | anchor: `normalize_items` | observation: The function normalizes every item through the same pure operation.
- B-1: workflow: normalize 1000 repeated items | method: command | command: python bench.py before | result: median 40 ms across 5 warm runs | confidence: high | evidence: F-1

## Capability Research
- R-1: component: not-applicable | version: not-applicable | source: not-applicable | finding: The selected patch is local and uses no ecosystem capability | target: B-1 | compatibility: not-applicable

## Candidate Decisions
- C-1: band: quick-win | impact: medium | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | change: normalize each distinct value once within the call and restore original order | benefit: reduce duplicate pure computation for repeated inputs | verify: V-1 | rollback: restore the direct list comprehension | operational-cost: one call-scoped bounded dictionary | experiment: none
- C-2: band: rejected | impact: low | confidence: low | effort: medium | risk: medium | verification-strength: missing | blast-radius: medium | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=no, compatibility=yes, verification=no, rollback=yes, operational-cost=no, decisions=yes | evidence: F-1, B-1, R-1 | change: add a process-wide cache | benefit: reuse values across calls | verify: V-2 | rollback: remove the cache | operational-cost: unbounded lifetime and invalidation ownership | experiment: none

## Recommended Plan
- Selected candidate: C-1
- Ordered changes: Add call-scoped reuse inside normalize_items, run focused parity tests, then rerun the same benchmark.
- Behavior guardrails: Keep caching call-scoped and preserve input order and exception behavior.
- H-1: stage: implementation | next: finish optimization | candidate: C-1

## Verification, Rollback, and Residual Risk
- V-1: proves: C-1 | method: run parity tests plus five warm benchmark runs | expected: byte-identical output and median below 25 ms.
- V-2: proves: C-2 | method: no accepted proof | expected: reject process-wide state.
- Rollback trigger: Any parity failure or median at or above 40 ms.
- Rollback action: Restore the direct list comprehension.
- Residual risk: Distinct-only workloads receive no improvement but retain bounded overhead.

## Rejects, Deferrals, and Limitations
- X-1: target: C-2 | status: rejected | reason: Process-wide cache semantics and ownership are unjustified | evidence: F-1, B-1 | revisit: only with cross-call profiling and invalidation requirements.

## Execution Record
- E-1: candidate: C-1 | authorization: user requested this validated batching implementation | change: added call-scoped distinct-value reuse | result: parity tests passed and median fell to 18 ms | regression: V-1

## Before/After Verification
- B-2: workflow: normalize 1000 repeated items | method: command | command: python bench.py after | result: median 18 ms across 5 warm runs | confidence: high | evidence: F-1
- Comparison: B-1 -> B-2 used the same 1000-item workload, runtime, warm-cache state, and five-run median.
```
