# Optimization Evidence Protocol

This file is the canonical home for tracing, coverage, baseline, alignment, research, planning-evidence, and measurement anti-pattern rules used by the full path.

## Targeted Trace

Trace input → validation → core logic → data access → external calls → transformations → observable output or side effects. Record entry points, callers, configuration, data shape and volume, frequency, concurrency, lifecycle, errors, tests, observability, and deployment context. Stop only when every proposed leverage point has an F-n and the affected workflow is understood end to end.

## Sweep Coverage

1. Inventory subsystems from boundaries, entry points, manifests, deployment units, and build/test ownership.
2. Select applicable passes: runtime, frontend/rendering, backend/API, database/data, build/test/CI, dependencies/tooling, architecture/maintainability, developer experience, and framework/platform.
3. Create the complete subsystem/pass matrix before deep research.
4. Triage each pair cheaply from code, configuration, tests, metrics, and history.
5. Give every pair local evidence and one terminal status.
6. Deep-dive at most three highest-signal candidate surfaces per wave.
7. Give each deferral a priority, limitation, evidence, and concrete resume action.

Any deferral makes the sweep incomplete. The matrix proves breadth; the wave limit protects depth.

## Baselines

Measure the workflow the user named, not a convenient proxy.

- Reuse documented or CI commands.
- Record the exact command or static method, working directory, relevant environment, representative workload, cache state, timestamp, raw observations, variance, limitations, and confidence.
- Repeat noisy measurements, retain raw values, and report the median.
- Separate cold and warm results when both matter; compare like with like.
- Prefer read-only plans, safe fixtures, profiles, traces, bundle reports, query plans, and existing instrumentation.
- For maintainability or developer experience, bounded-static evidence is a complete, explicitly delimited observation such as propagation count, duplicated policy branches, setup steps, feedback stages, or navigation hops. It supports only the stated non-runtime claim.
- A blocked baseline names the missing access, data, or environment and a safe confirmation experiment. It caps the candidate at `investigate`.

Never invent a performance number. Reject cold-versus-warm comparisons, a single noisy run, tiny fixtures used for production claims, unrelated microbenchmarks, percentage-only results, or CI speed obtained by moving, hiding, or skipping failures.

## Request-to-Baseline Alignment

Maintain a temporary ledger:

`request statement | F/B evidence | optimization consequence | options | recommendation | answer | status`

Record mismatched bottlenecks, proxy metrics, missing thresholds, scope conflicts, hidden protected behavior, incompatible constraints, uncertain risk, and unclear acceptance or authorization. A gap is blocking if its answer can change the target, metric, scope, behavior, compatibility, risk, candidate, verification, rollback, or authorization.

Resolve repository facts locally. Ask up to three related product questions per round, citing the request and relevant F/B evidence. Explain the consequence, offer mutually exclusive options when feasible, and recommend the smallest independently measurable, behavior-preserving, repository-supported, reversible mechanism.

Re-run affected traces and baselines after an answer changes the boundary or workload. When no blocking gap remains, recap the workflow, threshold, scope, protected behavior, constraints, exclusions, risk, baseline limitations, and stage authorization; require explicit confirmation. Fold confirmed outcomes into the canonical artifact and discard the ledger.

## Ecosystem Research

Build a component/version/usage inventory only for B-n-selected components. Resolve installed version, configuration, execution mode, deployment target, direct/transitive ownership, and actual use. Consult a specific official source matching the resolved major version; prefer the same minor. Record only capabilities that address the leverage point and preserve required semantics.

Reject generic best practices, unsupported-version guidance, undirected configuration changes, and upgrades justified only by recency.

## Candidate Evidence and Planning

Each C-n owns one independently measurable and independently reversible mechanism. Consider configuration, supported native capability, duplicate-code removal, focused local code, boundary optimization, justified dependency addition, and justified upgrade only when locally plausible. Merge symptoms sharing one mechanism; split mechanisms that can be measured or reverted separately.

Plans identify dependency-ordered file and symbol areas, behavior invariants, compatibility, exact checks and expected results, rollout when applicable, rollback triggers/actions, and residual risks. No workflow, package feature, version, public behavior, metric, experiment, verification, rollout, or rollback choice may remain for the implementer.

Before implementation, reconfirm worktree state, the baseline, regression surface, selected candidate, and rollback. Apply one candidate and rerun the same workload and behavior checks. Preserve unrelated user changes. Treat inconclusive benefit as failed evidence unless a separately stated non-performance acceptance criterion passes.

## Reconciliation

Before finalizing, account for every coverage pair, baseline, research claim, candidate, rejection, deferral, verification, protected behavior, and handoff. Report skipped checks and measurement limitations explicitly.
