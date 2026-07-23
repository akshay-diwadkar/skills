# Optimization Promotion Rubric

Use this rubric as the single source of truth for candidate promotion and ordering. Do not multiply ordinal labels or add them into a synthetic ROI number.

## Anchored Dimensions

- **Impact** — `high`: meets or materially advances the named success threshold; `medium`: meaningful bounded improvement; `low`: marginal or disconnected benefit.
- **Confidence** — `high`: comparable measurement plus code-path evidence, or complete bounded static evidence; `medium`: credible local evidence with one explicit measurement or compatibility confirmation outstanding; `low`: intuition, generic best practice, or hidden-production assumptions.
- **Effort** — `low`: one focused reversible patch and existing verification; `medium`: several coordinated files or new focused tests/configuration; `high`: migration, broad rollout, new operations, or cross-team work.
- **Risk** — `low`: local, behavior-preserving, strongly verified, trivially reversible; `medium`: shared configuration, multiple paths, or changed runtime characteristics; `high`: public contracts, persistence, security, concurrency, deployment, shared caching, or release paths.
- **Verification strength** — `strong`: comparable direct workflow evidence and regression checks; `bounded`: complete static evidence or safe confirmation experiment; `missing`: no credible proof path.
- **Blast radius** — `low`: one cohesive owner; `medium`: several files or one shared subsystem; `high`: multiple subsystems, environments, teams, or users.

Also record reversibility, independence, operational cost, and net-complexity effect explicitly.

## Promotion Gates

Answer every gate `yes` or `no` with cited evidence:

1. `target`: named workflow and optimization mechanism are supported by local facts.
2. `baseline`: reproducible baseline or complete bounded static evidence exists.
3. `behavior`: protected behavior is preserved or a named authorization permits the change.
4. `compatibility`: resolved versions, configuration, runtime mode, plugins, and deployment support the change, or ecosystem research is not applicable.
5. `verification`: exact proof method and expected result are defined.
6. `rollback`: executable trigger and reversal are defined.
7. `operational-cost`: CPU, memory, storage, network, security, observability, deployment, and maintenance effects are acceptable.
8. `decisions`: the candidate is independent and no blocking product or ownership choice remains.

## Deterministic Bands

### Quick Win

All gates are `yes`; confidence is high; impact is medium or high; effort and risk are low; verification is strong; the change is independent and reversible.

### Strategic Win

All gates are `yes`; impact is high; verification is at least bounded; the change is independent and reversible; and effort, risk, or blast radius is medium/high. Produce a full implementation-planning handoff.

### Investigate

Only `baseline` or `compatibility` may be `no`, and the candidate names a safe, concrete confirmation experiment. Do not authorize implementation or describe it as a win.

### Rejected

Use when target linkage is weak, impact is low, evidence is low-confidence, the version is unsupported, behavior change is unauthorized, risk or operational cost is unacceptable, verification/rollback is missing, or the candidate is not independently actionable. Record reason and revisit condition.

## Ordering Within Bands

Sort lexicographically by:

1. higher impact;
2. higher confidence;
3. stronger verification;
4. lower effort;
5. lower risk;
6. lower blast radius;
7. reversible before irreversible;
8. independent before dependent;
9. candidate ID.

The first option does not win automatically. Compare in this order when semantics fit: configure an existing capability, adopt a supported direct capability, remove duplicate custom machinery, make a focused local change, add a dependency only when total complexity falls, then upgrade only for a named locally unavailable capability or fix.

## Plan Acceptance

Do not finalize while the implementer must choose the workflow, package feature, version assumption, public behavior, metric, confirmation experiment, verification, rollout, or rollback. Every recommended candidate needs an observable acceptance threshold and a checker-passing artifact.
