---
name: design-codebase-with-senior-dev
description: Assess whether architectural change is justified and choose the smallest evidence-backed design, with an incremental behavior-preserving migration path. Use for boundary, dependency-direction, or state-ownership redesign, design-pattern evaluation or removal, and subsystem restructuring. Assessment-only — produces no code; route approved designs to plan-with-senior-dev.
---

# Design Codebase With Senior Dev

Determine whether the codebase needs a structural change at all. Reconstruct the current design from repository evidence, expose the forces that make it costly or unsafe, and choose the least powerful design that resolves those forces without silently changing behavior.

This skill is **assessment-only**. Inspect and run non-mutating checks, but never edit implementation files. Finish with a validated `Codebase Design Assessment` and a deterministic handoff.

## Non-Negotiables

1. **Admission rule:** introduce or retain an in-scope pattern only when current, evidenced change pressure or correctness risk repays its indirection, concepts, runtime behavior, migration cost, and long-term ownership.
2. **Removal rule:** remove an in-scope pattern only when its present protection is worth less than its cognitive and operational cost, and its contracts can be preserved through an incremental, reversible migration.
3. Preserve public APIs, schemas, events, files, CLIs, persistence, errors, side effects, user workflows, and operational promises unless explicit authorization names the permitted change.
4. Prefer L0 over L1, L1 over L2, and L2 over L3 whenever the lower level satisfies the evidenced constraints.
5. A fashionable pattern name, long file, large class, duplicate branch, disliked abstraction, or clean diagram is never sufficient evidence.
6. Reconcile the requested design with grounded pressures and protected contracts, then obtain explicit confirmation of the resolved design brief before classification or approval.

## Evidence Records

Use stable records throughout the assessment:

- `F-n` — verified fact with an existing `path:line`, anchor, and observation.
- `P-n` — ranked structural pressure citing the facts that establish its cost or risk.
- `C-n` — protected contract classified as `preserved`, `authorized-change`, or `at-risk`.
- `D-n` — selected L0-L3 decision, cited reasons, and nearest rejected level or option.
- `A-n` — assumption with status, impact, and verification path.
- `O-n` — serious alternative with level, concept cost, strongest arguments, and revisit trigger.
- `G-n` — pattern decision for a pattern introduced, removed, or deliberately relied upon by the scoped design.
- `V-n` — exact command, test, or manual check and its expected observable result.
- `M-n` — reversible L2/L3 migration slice with proof, rollback, and cleanup.
- `R-n` — residual risk with severity, scenario, consequence, owner, and follow-up.
- `H-n` — assessment-only handoff state.

Label narrative claims as `[Fact]`, `[Inference]`, `[Decision]`, or `[Assumption]` when they are not already expressed by one of these records. Do not guess a repository fact or erase contradictory evidence.

## Reference and Tool Routing

1. Read `references/design-decision-rubric.md` before classifying the change. Apply the analysis dimensions and simplicity controls relevant to the scoped path; apply the full runtime and distributed-system analysis for L3.
2. Read only the matching scenario in `references/worked-examples.md` when the concern resembles conditional dispatch, volatile integrations, redundant abstraction stacks, or distributed processing.
3. `references/assessment-contract.json` is the executable source of truth for output sections and hard gates. Do not recreate its headings or field grammar from memory.
4. After the provisional level is grounded, generate the matching scaffold:
   ```bash
   python scripts/scaffold_assessment.py --level L0|L1|L2|L3
   ```
5. Before finalizing, validate from the repository root:
   ```bash
   python scripts/check_assessment.py --level <L0|L1|L2|L3> --repo-root <repo> <assessment>
   ```

## Workflow

Complete Gates 1-7 in order. If later evidence changes the level, regenerate the scaffold for the new level and re-run every applicable gate.

### Gate 1: Frame and Protect

- Restate the observable goal, audience, scope, exclusions, constraints, invariants, and success measures.
- Inspect repository guidance and worktree state before drawing conclusions.
- Inventory public, durable, user-visible, and operational contracts as `C-n` records. Default each to `preserved` unless the user explicitly authorizes a named change.
- Record assumptions as `A-n`. A blocking product, contract, state-ownership, or failure-semantics choice prevents design approval; do not choose it on the user's behalf.

**Completion gate:** scope and success are observable, protected contracts are recorded, and no discoverable repository fact is being asked of the user.

### Gate 2: Ground the Current Design

- Identify entry points, modules, packages, deployments, storage, queues, external systems, tests, configuration, observability, and ownership on the scoped path.
- Trace at least one real request, command, job, or event from input through owner and dependencies to side effect and observable outcome.
- Map responsibility, dependency direction, data/control flow, state ownership, consistency boundaries, failure paths, and deployment units.
- Find local analogues and use history only when it can prove churn, repeated propagation, or ownership boundaries.
- Record facts as canonical `F-n` citations. Directory names and diagrams may guide discovery but cannot establish current behavior.

**Completion gate:** current behavior, ownership, dependencies, state, failures, contracts, and at least one end-to-end flow are grounded in existing repository evidence.

### Gate 3: Align Request and Current Design

- Follow the request-to-evidence alignment protocol in `references/design-decision-rubric.md`. Maintain a temporary gap ledger; do not add it to the assessment contract.
- Grill the user on every gap that could change the goal, scope, protected contracts, ownership, failure semantics, migration constraints, success measures, or admissible design level. Ask up to three related questions per round with cited request/evidence, consequence, two to four options when feasible, and a repository-grounded recommendation.
- Incorporate answers and re-ground changed boundaries until no blocking gap remains. Then recap the resolved goal, audience, scope, exclusions, pressures, protected contracts, ownership, failure semantics, constraints, and success measures and require explicit confirmation, even when no mismatch was found.
- If the recap is corrected, restart alignment. If confirmation is unavailable, pause without approving or finalizing an assessment. Alignment confirmation does not authorize implementation.
- Fold confirmed outcomes into existing `P-n`, `C-n`, `D-n`, and `A-n` records and discard the ledger.

**Completion gate:** no blocking gap remains and the resolved design brief is explicitly confirmed.

### Gate 4: Rank Pressures and Classify L0-L3

Separate symptoms from structural causes and rank each accepted cause as `P-n` by correctness risk, frequency, blast radius, and cost of leaving it unchanged.

Apply this decision tree literally:

1. **L0 — No structural change:** choose L0 when no structural cause is demonstrated. Tests, evidence, naming, documentation, configuration, or a direct behavior fix may still be recommended.
2. **L1 — Local simplification:** choose L1 when an evidenced cause can be resolved inside one cohesive module without changing ownership or adding a shared boundary.
3. **L2 — Boundary redesign:** choose L2 only when evidence identifies an independently changing or externally volatile boundary, L1 is demonstrably insufficient, and the boundary has a precise owner and more stable contract than the details it hides.
4. **L3 — Architectural migration:** choose L3 only when cross-system pressure is proven, L2 is demonstrably insufficient, a system-level invariant and authoritative state owner are named, operational semantics are defined, and an incremental rollback path exists.

The caps are distinct:

- Missing evidence of an independently changing boundary caps the decision at **L1**.
- When evidence supports a boundary but not the L3-only obligations, cap the decision at **L2**, never L1.

Record exactly one canonical `D-n` classification citing both `F-n` and `P-n`.

**Completion gate:** the selected level satisfies its gate, every lower level has a concrete insufficiency argument when applicable, and no stronger level is admitted speculatively.

### Gate 5: Compare, Admit, and Attack

- For L0, compare the current design with direct targeted relief using at least two `O-n` records.
- For L1-L3, compare at least three serious options: keep/current with relief, the minimum sufficient design, and one credible stronger or differently shaped design.
- Give each option the same criteria: pressure fit, change level, behavior safety, net complexity, ownership, operational correctness, migration, repository/language fit, testability, security/performance, and revisitability.
- Run the complete 14-question admission test only for each pattern materially **introduced**, **removed**, or **deliberately relied upon** by the scoped decision. Do not inventory every pattern in the repository.
- Attack the leading option with concrete counterexamples: lower-level sufficiency, accidental contract changes, hidden coupling, ambiguous state or retry ownership, partial failure, coexistence, observability, rollback, and evidence that would make a rejected option win.
- Repair the design or lower its level. Do not leave an attack as an unowned risk list.

**Completion gate:** required alternatives exist, the selected option survives adversarial review, every applicable `G-n` is scoped and evidenced, and rejected options have revisit triggers.

### Gate 6: Define the Level-Specific Assessment

Use the generated scaffold and complete only the sections required by the selected level:

- **L0:** current design, evidence, targeted relief, verification, residual risk, and revisit trigger.
- **L1:** L0 obligations plus the cohesive local owner, concepts removed/retained, and behavior-preservation proof.
- **L2:** full alternatives and pattern gates plus target boundary, dependency direction, state/contract ownership, operational semantics, and reversible `M-n` migration slices.
- **L3:** all L2 obligations plus the full runtime/distributed hazard analysis, system invariant, deployment compatibility, durable-state evolution, reconciliation, and rollback compatibility.

For every L2/L3 `M-n`, state prerequisite, changed boundary, preserved `C-n`, proving `V-n`, rollback trigger, rollback action, and cleanup condition. Avoid unguarded dual writes; when dual operation is unavoidable, define source of truth, reconciliation, idempotency, ordering, and recovery.

Do not write file/symbol-level implementation instructions. The assessment owns structural diagnosis, target boundaries, and migration shape; `plan-with-senior-dev` owns the exact implementation specification.

**Completion gate:** every contract field is concrete, the assessment contains no scaffold placeholders, and the target design assigns responsibility, ownership, dependencies, failures, proof, and rollback at the depth required by its level.

### Gate 7: Validate and Handoff

- Run `check_assessment.py` and repair every diagnostic.
- Re-read citations, protected-contract statuses, classification, lower-level rejection evidence, pattern gates, migration proof, rollback, and residual risks after the last repair.
- Record exactly one `H-n` state:
  - `finish assessment` when the design is not approved or no further work is requested;
  - `plan-with-senior-dev` when the target design is approved but no decision-complete implementation specification exists;
  - `implement-with-senior-dev` only when an approved decision-complete plan already exists.
- Never edit implementation files, even when the request combines assessment and implementation. Complete this assessment, then hand off according to the state above.

**Completion gate:** the checker passes, no unowned blocking decision is presented as approved, and exactly one next owner is named.

## Pattern Admission Questions

For each applicable `G-n`, answer Q1-Q14 as `yes`, `no`, or `unknown` with evidence. Questions 1, 3, 4, 8, 9, 11, 13, and 14 are hard gates: `no` rejects the pattern and `unknown` blocks its approval.

1. Does it resolve a current evidenced pressure or correctness risk?
2. Is that pressure recurrent or tied to a demonstrably volatile boundary?
3. Are lower-level alternatives described and insufficient?
4. Does each abstraction have one precise responsibility and owner?
5. Is its contract more stable than the details it hides?
6. Does it reduce propagation across independently changing modules or contracts?
7. Does it constrain rather than hide dependencies?
8. Is affected state ownership unambiguous?
9. Are protected contracts preserved or explicitly authorized to change?
10. Can behavior and production outcomes be verified without mock-only proof?
11. Are applicable operational semantics explicit?
12. Does it fit repository and language idioms?
13. Can it be introduced in independently verifiable, reversible slices?
14. Does evidenced value exceed cognitive, runtime, operational, migration, and ownership cost?

## Handoff Boundaries

- Use `codebase-issue-auditor` before this skill when the structural concern has not yet been discovered and proven.
- Use `plan-with-senior-dev` after a target design is approved to produce an exact file/symbol-level implementation specification.
- Use `implement-with-senior-dev` only when that decision-complete plan is approved.
- Use `optimize-codebase-with-senior-dev` when the primary objective is measured performance, build/runtime efficiency, dependency/tooling leverage, or ecosystem capability.
