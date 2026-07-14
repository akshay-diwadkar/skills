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

## ROI Scoring and Tiered Ranking

After scoring each candidate on the standard dimensions, compute a qualitative ROI score to produce a ranked, tiered list.

### ROI Formula

ROI = (Impact × Confidence) / (Effort × Risk)

All factors use the dimension scores mapped to numeric weights:
- high = 3, medium = 2, low = 1

For dimensions where lower is better (Effort, Risk), the raw score is used as a cost multiplier. Higher ROI values indicate better return.

Example: A candidate with Impact=high(3), Confidence=high(3), Effort=low(1), Risk=low(1) scores ROI = 9.0 — a strong quick win. A candidate with Impact=high(3), Confidence=medium(2), Effort=high(3), Risk=medium(2) scores ROI = 1.0 — a strategic investment requiring justification.

### Tier Definitions

Assign each candidate to exactly one tier based on ROI score and qualitative judgment:

| Tier | ROI Range | Characteristics | Action |
| --- | --- | --- | --- |
| **Quick Win** | ROI ≥ 4.0 | High impact, low effort, low risk. Can be implemented independently and verified immediately. | Recommend first. Implement in any order. |
| **Strategic Win** | 1.5 ≤ ROI < 4.0 | High impact but requires meaningful effort, planning, or carries moderate risk. Worth doing but needs a proper plan. | Recommend after quick wins. Hand off to `plan-with-senior-dev` for implementation planning. |
| **Speculative** | 0.5 ≤ ROI < 1.5 | Uncertain benefit, high effort, or low confidence. Could pay off but evidence is incomplete. | Present with caveats. Recommend further investigation or measurement before committing. |
| **Rejected** | ROI < 0.5 or fails threshold | Low benefit relative to cost, unsupported by evidence, version-incompatible, or unacceptable risk. | Move to reject ledger with reason and revisit condition. |

### Ranked Ledger Format

Present the ranked candidates as an ordered list within each tier:

```
## Quick Wins (implement first)

### QW-1: {title}
- **What changes**: {concrete description of the change}
- **Why it helps**: {mechanism of improvement, linked to evidence}
- **Expected benefit**: {quantified or bounded estimate}
- **Effort**: {low/medium — specific: e.g., 'one config change' or '~50 lines across 2 files'}
- **Risk**: {low — specific: e.g., 'fully reversible, no behavior change'}
- **Evidence**: {doc URL, profile data, or code path reference}
- **ROI Score**: {numeric}

## Strategic Wins (plan then implement)

### SW-1: {title}
- {same fields as above}
- **Planning notes**: {what plan-with-senior-dev should focus on}

## Speculative (investigate further)

### SP-1: {title}
- {same fields as above}
- **Missing evidence**: {what needs to be confirmed before promoting}

## Rejected

### RJ-1: {title}
- **Reason**: {specific reason for rejection}
- **Revisit when**: {condition under which to reconsider}
```

### Ordering Within Tiers

Within each tier, order candidates by:
1. ROI score (descending)
2. Blast radius (ascending — prefer smaller scope)
3. Reversibility (most reversible first)
4. Independence (candidates with no dependencies on other candidates first)

### Sweep Mode Ranking

When running in broad sweep mode (no specific target), present the tiered list as a comprehensive optimization roadmap. Group related candidates when they share an affected subsystem but keep them independently implementable. Note dependencies between candidates when one enables or blocks another.

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
