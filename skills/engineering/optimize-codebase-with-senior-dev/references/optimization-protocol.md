# Optimization Protocol

Use this protocol to do the legwork behind the seven gates in `SKILL.md`. The JSON contract owns artifact shape; this reference owns evidence collection and completion discipline.

## Frame

Record the repository and audited commit, dirty-worktree state, target workflow or sweep request, goal, metric, constraints, exclusions, protected behavior, risk tolerance, output destination, and plan/implementation authorization. Resolve repository facts locally. Ask only about product choices that materially change the optimization.

## Targeted Trace

Trace input → validation → core logic → data access → external calls → transformations → output or side effects. Record entry points, callers, configuration, data shape and volume, concurrency, lifecycle, error handling, tests, observability, and deployment context. Stop tracing when every proposed leverage point can be tied to an existing `F-n` and the affected workflow is end-to-end understood.

## Sweep Coverage

1. Inventory subsystems from repository boundaries, entry points, manifests, deployment units, and build/test ownership.
2. Select applicable passes: runtime, frontend/rendering, backend/API, database/data, build/test/CI, dependencies/tooling, architecture/maintainability, developer experience, framework/platform.
3. Create the full subsystem/pass matrix before deep research.
4. Triage each pair cheaply from code, configuration, tests, existing metrics, and history.
5. Mark it `candidate`, `clean`, `rejected`, or `deferred`; every record needs local evidence.
6. Deep-dive at most three highest-signal candidate surfaces in one wave. Use impact, current evidence, user priority, and risk to choose them.
7. Give every deferral a priority and resume action. High-priority deferrals must appear in limitations. A sweep with any deferral is incomplete.

The matrix proves breadth; the wave limit protects depth. Never substitute a sample of interesting files for coverage.

## Baselines

- Measure the workflow the user named, not a convenient proxy.
- Reuse documented or CI commands. Record exact command, directory, relevant environment, representative workload, cache state, timestamp, raw observations, variance, limitations, and confidence.
- Repeat noisy measurements and report raw values plus median. Separate cold and warm results when both matter.
- Prefer read-only plans, safe fixtures, profiles, traces, bundle reports, and query plans before adding instrumentation.
- For maintainability or DX, bounded static evidence may measure propagation count, duplicated policy, setup steps, feedback delay, or navigation cost.
- A blocker must name the missing access/data/environment and a safe experiment. It caps promotion at `investigate`.

Reject cold-versus-warm comparisons, single noisy runs, tiny fixtures used for production claims, unrelated microbenchmarks, percentage-only claims, or CI speed obtained by moving or hiding failures.

## Request-to-Baseline Alignment

After tracing and baselining, maintain a temporary ledger:

`request statement | repository or baseline evidence | optimization consequence | options | recommendation and reason | answer | status`

Record mismatched bottlenecks, proxy metrics, missing success thresholds, scope conflicts, hidden protected behavior, incompatible constraints, uncertain risk tolerance, and unclear candidate acceptance or stage authorization. A gap is blocking when its answer could change the target workflow, metric, scope, protected behavior, compatibility, constraints, risk, candidate eligibility, verification, rollback, or authorization. Discover repository facts locally and decide low-impact reversible details from precedent.

Ask up to three related blocking questions per round. Cite the request and relevant `F-n` or `B-n` evidence, explain the affected optimization decision, offer two to four mutually exclusive options when feasible, and mark the recommended option with a reason grounded in comparable measurement, behavior preservation, repository support, reversibility, and the smallest independently measurable mechanism.

Record answers and re-run affected traces or baselines whenever the boundary or workload changes. Repeat until no blocking gap remains. Then recap the target workflow, measurable success, scope, protected behavior, constraints, exclusions, risk tolerance, baseline limitations, and plan/implementation authorization and require explicit confirmation. Corrections restart the loop; missing confirmation blocks a final approved report or implementation.

Translate confirmed outcomes into existing brief, baseline, protected-behavior, candidate, verification, and authorization fields and discard the ledger. Alignment confirmation does not authorize implementation; implementation still requires the existing explicit execution gate.

## Candidate Construction

Each `C-n` owns one independently measurable mechanism. Compare configuration, supported native capability, duplicate-code removal, focused local code, boundary optimization, justified dependency addition, and justified upgrade only when each is plausible.

Record:

- workflow and mechanism;
- expected benefit and evidence references;
- impact, confidence, effort, risk, verification strength, and blast radius;
- behavior preservation and compatibility;
- reversibility, independence, operational cost, and net-complexity effect;
- exact verification, rollback, and confirmation experiment when needed;
- deterministic band and all promotion-gate answers.

Do not bundle unrelated optimizations. Merge symptoms that share one mechanism; split candidates that can be measured or reverted independently.

## Planning and Execution

A plan states dependency-ordered file areas and symbols, behavioral invariants, compatibility, exact checks and expected results, rollout when applicable, rollback triggers/actions, and residual risks. It must leave no target, feature, metric, interface, verification, or rollback choice to the implementer.

Implementation requires explicit authorization and a checker-passing report. Reconfirm the worktree, baseline, regression surface, selected candidate, and rollback before editing. Apply one candidate. Re-run the same workload and behavior checks. Preserve unrelated user changes. Treat inconclusive benefit as failed evidence unless another stated non-performance goal independently meets acceptance criteria.

## Reconciliation

Before finalizing, account for every subsystem/pass pair, candidate, rejection, deferral, baseline, research claim, verification, and protected behavior. Run the checker, repair findings, and name one handoff. Report skipped checks and live-evaluation limitations explicitly.
