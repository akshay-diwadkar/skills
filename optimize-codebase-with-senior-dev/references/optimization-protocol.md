# Optimization Protocol

Use this protocol for optimization work from a known target. Keep artifacts in working notes unless the user asks for a report.

## Working Artifacts

- **Optimization brief**: target, workflow, pain signal, category, constraints, exclusions, success metric, risk tolerance, authorization level, and output mode.
- **System frame**: repo purpose, target subsystem, runtime, deployment surface, test/build/CI shape, guidance, and traced workflow.
- **Ecosystem inventory**: relevant runtimes, frameworks, direct/dev/transitive dependencies, resolved versions, plugins, platforms, config, and usage state.
- **Capability matrix**: component and version, current use, applicable native capability, target link, local evidence, official evidence, adoption type, compatibility, and operational cost.
- **Baseline record**: command, directory, environment, workload, cache state, raw measurements, variance, confidence, and limitations.
- **Candidate ledger**: leverage point, benefit, files/subsystems, ecosystem fit, compatibility, effort, risk, blast radius, reversibility, operational cost, net complexity, verification, side effects, and decision.
- **Ranking matrix**: candidate scores from `optimization-rubric.md` plus user constraints.
- **Implementation plan**: chosen strategy, ordered steps, guardrails, checks, acceptance criteria, rollback, and residual risks.
- **Execution record**: authorization, patch scope, behavior checks, baseline reruns, deviations, and keep/narrow/revert decision.
- **Verification record**: comparable before/after results, regression checks, ecosystem/version evidence, conclusion, and residual risks.
- **Reject ledger**: rejected or deferred candidates, evidence, reason, and revisit condition.
- **Repo comprehension map**: repo purpose, domain model, architecture overview, major workflows with entry-to-exit traces, data flow, deployment model, and component interaction map.
- **Documentation research log**: per-component records of version, doc URLs consulted, specific findings, current state in repo, recommended state per docs, expected benefit, confidence, and compatibility notes.
- **Optimization surface analysis**: per-component delta between current repo usage and documented capabilities, cross-component boundary opportunities, and domain-specific optimization findings.
- **ROI-ranked candidate ledger**: tiered list (Quick Win, Strategic Win, Speculative, Rejected) with ROI scores, ordered within each tier by ROI, blast radius, reversibility, and independence.
- **Plan-with-senior-dev handoff brief**: for each approved candidate, a structured brief containing target, goal, constraints, success criteria, affected files and subsystems, ecosystem evidence, baseline reference, and verification approach formatted for consumption by `plan-with-senior-dev`.

## Required Sequence

1. Trace the named workflow OR, in sweep mode, trace all major workflows and identify likely leverage points.
2. Build a repo comprehension map covering purpose, domain, architecture, workflows, data flow, deployment, and component interactions.
3. Build the relevant ecosystem inventory and capability matrix.
4. Research official documentation for each significant component via web search and URL reading. Record findings in the documentation research log.
5. Produce the optimization surface analysis by cross-referencing actual repo usage against documented capabilities, including cross-component boundary opportunities.
6. Establish a baseline or document why measurement is unavailable.
7. Generate at least two credible candidates when alternatives exist. Score each with the ROI formula and assign to tiers.
8. Rank candidates within tiers and record rejects before planning implementation.
9. For each approved candidate, produce a plan-with-senior-dev handoff brief. Recommend invoking `plan-with-senior-dev` for Strategic Win candidates.
10. Implement only with explicit authorization, one measurable candidate at a time.
11. Re-run behavior checks and the comparable baseline before claiming success.

Do not skip ecosystem inventory merely because the likely change appears to be local code. A framework default, package capability, build transform, ORM behavior, or runtime mode may define the actual leverage point.

Do not skip documentation research. The delta between what the repo does and what official docs recommend is often the highest-ROI optimization surface.

## Optimization Passes

Run only passes that can affect the brief.

### Runtime Hot Path

Inspect call paths, data sizes, algorithmic scaling, repeated I/O, serialization, startup, memory, allocation, scheduling, concurrency, and network boundaries. Prefer profiles, traces, focused timings, logs, or clear source-path evidence.

### Build, Test, and CI

Inspect task graphs, incremental modes, caches and keys, duplicate setup, test selection, workers, sharding, artifact reuse, flaky retries, job dependencies, and feedback latency. Preserve coverage and failure visibility.

### Dependency and Tooling

Inspect manifests, lockfiles, resolved versions, package-manager behavior, config, overlapping tools, generated-code boundaries, plugins, and direct versus transitive use. Compare configuration-first, native-capability, local-code, new-dependency, and upgrade options.

### Architecture and Maintainability

Inspect coupling, duplicated policy, ownership, change locality, dead complexity, pass-through wrappers, testability, and agent navigation. Prefer behavior-preserving deletion or simplification before new abstractions.

### Developer Experience

Inspect setup, command discoverability, feedback loops, docs, error messages, local/CI parity, repo maps, and repeated human or agent navigation cost.

### Framework and Platform

Follow `ecosystem-leverage.md`. Confirm the resolved version and execution mode before evaluating native rendering, data loading, caching, compilation, querying, scheduling, deployment, or observability capabilities.

## Safe Baseline Collection

- Use existing documented, scripted, or CI commands where possible.
- Record exact command, working directory, relevant environment, representative input, cache state, and timestamp.
- Measure the workflow the user cares about, not a convenient proxy.
- Use repeated runs for noisy measurements and report raw values plus a robust summary such as median.
- Separate cold and warm results when both are operationally relevant.
- Keep production-affecting commands read-only unless side effects are explicitly approved.
- Prefer safe fixtures, staging data, captured traces, or read-only plans for databases and external systems.
- Use existing bundle analyzers, profilers, query tools, and test reports before adding instrumentation.
- Record static evidence with lower confidence when direct measurement is blocked.

## Measurement Traps

- Different workload, hardware, runtime version, environment, or configuration before and after.
- Cold-cache baseline compared with warm-cache result.
- One noisy run presented as proof.
- Microbenchmark improvement that does not improve the named workflow.
- Tiny fixtures used to justify production-scale claims.
- Dependency downloads or unrelated caches attributed to the patch.
- Throughput gains that worsen latency, memory, correctness, cost, or failure recovery.
- CI speed gained by moving failures later, skipping coverage, or hiding errors.
- Percentage claims without raw values and variance.

## Execution and Revert Rules

- Establish behavior checks and rollback before editing.
- Keep each patch attributable to one candidate.
- Stop on failed compatibility assumptions or behavior regression.
- Revert only changes introduced by the optimization run; preserve unrelated worktree changes.
- Treat an inconclusive performance result as failed evidence. Keep the patch only when another stated goal, such as verified complexity reduction, independently satisfies acceptance criteria.
- Record deviations from the plan before continuing.

## Reject Ledger

For each reject record candidate, reason, evidence or missing evidence, and revisit condition. Common reasons include weak target linkage, unsupported installed version, transitive-only API, custom semantics not covered by the native feature, low confidence, high blast radius, poor reversibility, increased operational cost, net complexity growth, unavailable verification, or unapproved behavior change.
