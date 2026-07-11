# Optimization Rubric

Use this rubric to decide which candidates deserve planning or implementation.

## Scoring Dimensions

Score each dimension as `high`, `medium`, or `low`. For effort, risk, blast radius, and operational cost, lower is better.

- **Impact**: expected improvement to the named workflow, cost, reliability, maintainability, or feedback loop.
- **Confidence**: strength of baseline, profiling, source-path evidence, local metadata, and version-matched documentation.
- **Effort**: implementation, review, test, documentation, migration, and rollout cost.
- **Risk**: likelihood of regression, incompatibility, operational failure, or hidden production effect.
- **Reversibility**: ability to undo the change without data, contract, deployment, or workflow damage.
- **Blast radius**: files, subsystems, commands, environments, teams, or users affected.
- **Verification strength**: quality of before/after measurement and behavior checks.
- **Ecosystem fit**: how directly the candidate uses a supported capability of the actual local stack without fighting established patterns.
- **Compatibility certainty**: evidence that the resolved version, configuration, runtime mode, plugins, and deployment target support the candidate.
- **Operational cost**: ongoing memory, CPU, storage, network, cache, observability, deployment, security, and maintenance burden.
- **Net-complexity effect**: whether total concepts, custom code, configuration, dependencies, and ownership decrease or increase.

## Recommendation Threshold

Recommend a candidate only when it is:

- high confidence, or medium confidence with a concrete confirmation step before implementation;
- linked to the named target and root cause;
- supported by a reproducible baseline or appropriately bounded static evidence;
- independently reviewable and behavior-preserving by default;
- compatible with the resolved ecosystem or accompanied by a separately justified migration;
- reversible enough for the user's risk tolerance;
- neutral or favorable in operational cost and net complexity, unless the measured benefit explicitly justifies the tradeoff.

Hold back low-confidence, unsupported-version, transitive-only, high-blast-radius, or weakly verifiable options unless the user asks for speculative alternatives. Record the evidence needed to revisit them.

## Risk Levels

- **Low**: local, behavior-preserving, strongly verified, and trivially reversible.
- **Medium**: touches shared config or several files, changes runtime characteristics, or has incomplete environment coverage.
- **High**: affects public APIs, persistence, deployment, release gates, framework/runtime modes, shared caching, concurrency, or broad code paths.
- **Critical**: risks data loss, security exposure, outage, broken releases, irreversible migration, or widespread behavior change.

## Confidence Levels

- **High**: direct measurement plus clear code-path evidence; ecosystem claims match the resolved version and local configuration.
- **Medium**: credible local evidence with one explicit measurement or compatibility question remaining.
- **Low**: intuition, generic best practice, latest-version docs applied to an older version, hidden production assumptions, or unmeasured symptoms.

## Ecosystem Decision Order

Prefer the first option that passes the threshold:

1. Configure a capability already present and supported.
2. Adopt an unused native capability in the installed framework or direct dependency.
3. Remove or simplify custom code that duplicates supported behavior without required custom semantics.
4. Make a focused local-code optimization.
5. Add a dependency only when total complexity and operational cost decrease.
6. Upgrade only for a specific required capability or fix with a compatibility and rollback plan.

This order is a comparison discipline, not an automatic winner. Reject a native capability when it obscures required behavior, performs worse for the workload, lacks observability, or creates unacceptable coupling.

## Acceptance Criteria for a Plan

An acceptable plan has:

- a clear target, workflow, constraints, success metric, and risk tolerance;
- baseline or bounded static evidence;
- relevant ecosystem inventory and resolved versions;
- a capability-to-target link with local and official evidence where applicable;
- proposed change mapped to the root cause;
- behavior preservation, compatibility, and operational effects addressed;
- exact verification commands and before/after criteria;
- rollback path and residual risks;
- rejected alternatives with reasons when meaningful options existed.

Do not finalize while the implementer must choose the target, package/framework feature, version assumptions, metric, public behavior, verification path, or rollback.

## Authorization Threshold for Execution

Implement only when the user explicitly requested code changes and the chosen candidate passes the recommendation threshold. Before editing, require a baseline, regression surface, exact patch scope, compatibility evidence, acceptance criteria, and rollback. Do not interpret a request for analysis, options, or a plan as implementation authorization.
