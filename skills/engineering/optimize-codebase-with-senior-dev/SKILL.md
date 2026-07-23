---
name: optimize-codebase-with-senior-dev
description: Optimize a named bottleneck, workflow, or tooling pain with evidence-backed changes that preserve behavior — planning first, implementation only on explicit request. Also runs repository-wide optimization sweeps when asked. Use for performance, build, CI, dependency, or developer-experience targets; for finding unknown problems, use codebase-issue-auditor.
---

# Optimize Codebase With Senior Dev

Find the highest-leverage way to improve a named workflow without silently changing behavior. Use **targeted** scope for a known pain or finding. Use **sweep** scope only when the user explicitly asks for repository-wide optimization discovery.

Planning is mandatory. Implementation remains available only after the planning artifact validates and the user explicitly authorizes code changes. Prefer configuration and supported capabilities already present in the resolved stack over custom machinery, new dependencies, upgrades, or rewrites.

## Non-Negotiables

1. Evidence selects the leverage point; documentation does not create one.
2. Preserve APIs, outputs, errors, side effects, persistence, security, release gates, and operational promises unless the user names an authorized change.
3. Establish a comparable baseline or bounded static evidence before researching an ecosystem solution.
4. Never rank candidates with ordinal arithmetic. Apply the deterministic promotion gates in `references/optimization-rubric.md`.
5. Sweep breadth is coverage-accounted and depth-bounded. Deferred work is visible and resumable.
6. Never implement from an unvalidated report or execute more than one candidate at a time.
7. Reconcile the requested workflow and success metric with tracing and baseline evidence, then obtain explicit confirmation before researching or selecting candidates.

## Canonical Records

- `F-n` — verified local fact with an existing `path:line`, anchor, and observation.
- `CV-n` — subsystem/pass coverage with terminal status, evidence, priority, and resume action.
- `B-n` — raw baseline or bounded static/blocked measurement record.
- `R-n` — version-matched official research tied to a `B-n`, or an explicit not-applicable record.
- `C-n` — independently measurable candidate with promotion gates and deterministic band.
- `V-n` — exact check and expected observable result.
- `X-n` — rejection or deferral with evidence and revisit condition.
- `H-n` — exactly one next owner.
- `E-n` — explicitly authorized implementation action and result; implementation stage only.

## Contract and Reference Routing

1. Read `references/optimization-protocol.md` before starting non-trivial work.
2. `references/optimization-contract.json` is the executable source of truth for output sections, records, bands, and sweep limits. Do not recreate its grammar from memory.
3. Generate the artifact before filling it:
   ```bash
   python scripts/scaffold_optimization.py --scope targeted|sweep --stage plan|implementation
   ```
4. Read `references/optimization-rubric.md` before classifying candidates.
5. Read `references/ecosystem-leverage.md` and `references/docs-research-protocol.md` only after a `B-n` or evidenced static leverage point names a relevant component.
6. Read only the applicable pass in `references/optimization-patterns.md`. Read only the matching example in `references/worked-examples.md`.
7. Validate before finalizing:
   ```bash
   python scripts/check_optimization.py --scope targeted|sweep --stage plan|implementation --repo-root <repo> <report>
   ```

## Eight Gates

Complete Gates 1-8 in order. If later evidence changes scope, stage, or the selected candidate, regenerate the scaffold and re-run every affected gate.

### Gate 1: Frame and Protect

- Inspect repository guidance and worktree state before asking questions.
- Record scope, stage, authorization, named workflow, observable goal, success metric, constraints, exclusions, and risk tolerance.
- State protected behavior. Treat implementation as unauthorized unless the user explicitly requested edits.
- Record blocking product choices rather than deciding them on the user's behalf.

**Completion gate:** target and success are observable, authorization is exact, protected behavior is explicit, and no discoverable repository fact is being asked of the user.

### Gate 2: Trace and Cover

For targeted scope, trace the workflow from entry point through validation, core logic, I/O, external calls, transformations, and observable outcome. Record relevant data sizes, frequency, concurrency, and failure behavior.

For sweep scope:

- Inventory stable subsystem IDs and applicable optimization passes.
- Create exactly one `CV-n` for every subsystem/pass pair with `candidate`, `clean`, `rejected`, or `deferred` status.
- Use a lightweight repository-wide pass first. Deep-dive at most three highest-signal candidate surfaces per wave.
- Give every deferral a priority, limitation, evidence, and concrete resume action.
- Mark the sweep `incomplete` while any coverage record is deferred.

**Completion gate:** the targeted path is end-to-end grounded, or the sweep matrix is complete with no silent omissions and no more than three candidate surfaces in the current wave.

### Gate 3: Baseline the Named Workflow

- Prefer existing commands, profiles, timings, query plans, bundle reports, CI data, dependency metadata, or change-propagation evidence.
- Record command or method, directory, workload, environment, cache state, raw result, variance, limitations, and confidence.
- Use bounded static evidence for maintainability or DX when timing is not the claimed benefit. Never invent a performance number.
- If measurement is blocked, state why and cap the candidate at `investigate` until a safe confirmation experiment succeeds.

**Completion gate:** every candidate surface has a `B-n` that measures the named workflow, supplies bounded static evidence, or records an actionable blocker.

### Gate 4: Align Request and Baseline Evidence

- Follow the request-to-baseline alignment protocol in `references/optimization-protocol.md`. Maintain a temporary gap ledger outside the optimization artifact.
- Grill the user on every gap that could change the target workflow, success metric, scope, protected behavior, constraints, exclusions, risk tolerance, compatibility, candidate acceptance, or stage authorization. Ask up to three related questions per round with request/evidence, consequence, two to four options when feasible, and an evidence-backed recommendation.
- Incorporate answers and re-run affected tracing or baselines until no blocking gap remains. Then recap the target, measurable success, scope, protected behavior, constraints, exclusions, risk tolerance, baseline limitations, and stage authorization and require explicit confirmation even when no mismatch was found.
- Corrections restart alignment. Missing confirmation pauses the skill without a final approved report or implementation. Alignment confirmation does not authorize implementation or external effects.
- Fold confirmed outcomes into existing brief, baseline, protected-behavior, candidate, and authorization fields and discard the ledger.

**Completion gate:** no blocking gap remains and the resolved optimization brief is explicitly confirmed.

### Gate 5: Research the Evidence-Selected Components

- Build the relevant component/version/usage inventory only for components connected to a `B-n`.
- Confirm resolved version, configuration, execution mode, deployment target, direct/transitive ownership, and actual use.
- Consult specific official documentation matching the resolved major version; same minor is preferred.
- Record only capabilities that address the evidenced leverage point and preserve required semantics.
- Reject generic best practices, unsupported versions, undirected configuration deltas, and “upgrade because newer.”

**Completion gate:** each ecosystem claim has local usage evidence, a version-matched URL, compatibility analysis, and a direct link to a baseline; local-code candidates carry an explicit not-applicable `R-n`.

### Gate 6: Compare and Classify

- Generate at least two credible candidates when alternatives exist, including the smallest direct or configuration option.
- Record impact, confidence, effort, risk, verification strength, blast radius, reversibility, independence, operational cost, expected benefit, verification, and rollback.
- Apply every promotion gate from `references/optimization-rubric.md` literally.
- Classify each candidate as `quick-win`, `strategic-win`, `investigate`, or `rejected` without arithmetic.
- Keep rejected and deferred options as `X-n` records with revisit conditions.

**Completion gate:** every candidate has one deterministic band, all gate answers are evidenced, the selected option beats serious alternatives under the user's constraints, and ordering follows the rubric's tie-breaks.

### Gate 7: Plan, Then Optionally Implement

For plan stage, produce dependency-ordered changes with exact file areas, behavior guardrails, compatibility, tests, acceptance criteria, rollback, residual risk, and one `H-n`. Strategic Wins should hand off to `plan-with-senior-dev` when further implementation-level specification is needed.

For implementation stage:

1. Require explicit authorization in the brief and `E-n`.
2. Require a checker-passing plan whose selected candidate is an eligible Quick or Strategic Win.
3. Confirm regression coverage and a comparable baseline before editing.
4. Apply one independently measurable candidate as a minimal patch.
5. Run focused behavior checks and the comparable baseline.
6. Stop, narrow, or revert only the introduced patch when behavior regresses, compatibility fails, or benefit is inconclusive.

**Completion gate:** plan stage is decision-complete without edits, or implementation stage contains one authorized candidate with an attributable patch, comparable evidence, and rollback status.

### Gate 8: Validate and Handoff

- Run `check_optimization.py` and repair every diagnostic.
- Re-read citations, coverage, baselines, research/version claims, candidate gates, verification, rollback, authorization, deferrals, and residual risks after the last repair.
- Emit exactly one `H-n`: `finish optimization`, `plan-with-senior-dev`, or `implement-with-senior-dev`.
- Report neutral, worse, or inconclusive results honestly; do not claim weaker-model reliability without a completed live evaluation.

**Completion gate:** the checker passes, no blocking decision is disguised as settled, sweep limitations are explicit, and exactly one next owner is named.

## Handoff Boundaries

- Use `codebase-issue-auditor` when bugs, risks, or architectural problems have not yet been proved.
- Use `codebase-issue-auditor` for a concrete defect or regression that must be reproduced, audited, and isolated.
- Use `plan-with-senior-dev` for a Strategic Win requiring exact implementation contracts and propagation.
- Use `implement-with-senior-dev` for an approved decision-complete plan, or retain this skill's implementation stage when the user explicitly requests the measured candidate directly.
- Use `design-codebase-with-senior-dev` when the primary objective is structural redesign rather than measurable optimization.
