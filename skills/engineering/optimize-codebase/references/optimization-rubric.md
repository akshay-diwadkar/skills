# Optimization Promotion Rubric

This file is the canonical home for full-path candidate dimensions, promotion, rejection, and ordering. Never multiply or sum ordinal labels into synthetic ROI.

## Dimensions

- **Impact** — `high`: meets or materially advances the success threshold; `medium`: meaningful bounded improvement; `low`: marginal or disconnected.
- **Confidence** — `high`: comparable measurement plus path evidence, or complete bounded-static evidence; `medium`: credible local evidence with one confirmation outstanding; `low`: intuition or hidden-production assumptions.
- **Effort** — `low`: one focused reversible patch with existing verification; `medium`: coordinated files or focused new tests/configuration; `high`: migration, rollout, operations, or cross-team work.
- **Risk** — `low`: local, behavior-preserving, strongly verified, and trivially reversible; `medium`: shared configuration, multiple paths, or changed runtime characteristics; `high`: public contracts, persistence, security, concurrency, deployment, caching, or release paths.
- **Verification strength** — `strong`: comparable workflow evidence plus regression checks; `bounded`: complete static evidence or a safe confirmation experiment; `missing`: no credible proof path.
- **Blast radius** — `low`: one cohesive owner; `medium`: several files or one shared subsystem; `high`: multiple subsystems, environments, teams, or users.

Also record reversibility, independence, operational cost, and net-complexity effect.

## Promotion Gates

Answer every gate `yes` or `no` with cited evidence:

1. `target`: local facts support the workflow and mechanism.
2. `baseline`: a reproducible baseline or complete bounded-static baseline exists.
3. `behavior`: protected behavior is preserved or explicitly authorized to change.
4. `compatibility`: resolved versions, configuration, runtime mode, plugins, and deployment support the change, or research is not applicable.
5. `verification`: exact proof and expected result are defined.
6. `rollback`: executable trigger and reversal are defined.
7. `operational-cost`: CPU, memory, storage, network, security, observability, deployment, and maintenance effects are acceptable.
8. `decisions`: the candidate is independent and no blocking product or ownership choice remains.

## Bands

### Quick Win

All gates are `yes`; confidence is high; impact is medium or high; effort, risk, and blast radius are low; verification is strong; the change is independent and reversible.

### Strategic Win

All gates are `yes`; impact is high; verification is at least bounded; the change is independent and reversible; and effort, risk, or blast radius is medium/high. Produce the dedicated plan-change request when the handoff owner is `plan-change`.

### Investigate

Only `baseline` or `compatibility` may be `no`, and the candidate names a safe confirmation experiment. Do not authorize implementation or call it a win.

### Rejected

Reject weak target linkage, low impact or confidence, unsupported versions, unauthorized behavior changes, unacceptable risk or operational cost, missing verification/rollback, or non-independent mechanisms. Record evidence and a revisit condition.

## Ordering

Sort lexicographically by:

1. band in contract order;
2. higher impact;
3. higher confidence;
4. stronger verification;
5. lower effort;
6. lower risk;
7. lower blast radius;
8. reversible before irreversible;
9. independent before dependent;
10. candidate ID.

When semantics fit, compare mechanisms in this order: configure an existing capability, adopt a supported direct capability, remove duplicate custom machinery, make a focused local change, add a dependency only when total complexity falls, then upgrade only for a named unavailable capability or fix.

Do not finalize while a material implementation choice remains.
