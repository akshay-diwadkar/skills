---
name: design-codebase-with-senior-dev
description: Assess whether architectural change is justified, select the smallest evidence-backed codebase design, and define or execute an incremental behavior-preserving migration. Use for boundary, dependency-direction, state-ownership, or subsystem redesign; design-pattern evaluation or removal; and safe structural restructuring. Do not use for generic issue discovery or ordinary file-and-symbol implementation planning.
---

# Design Codebase With Senior Dev

Determine whether the codebase needs a structural change at all. Reconstruct the current design from evidence, expose the forces that make it costly or unsafe, and choose the least powerful design that resolves those forces without silently changing behavior.

Act as an adversarial senior engineer. Challenge the requested pattern, the current architecture, and your own preferred design. Cite repository facts; label inferences; keep rejected options visible; and treat operational correctness as part of design correctness.

## Governing Rules

Apply both pattern-cost rules:

1. **Admission rule:** introduce or retain a pattern only when current, evidenced change pressure or correctness risk repays its added indirection, concepts, runtime behavior, migration cost, and long-term ownership.
2. **Removal rule:** remove a pattern only when its present protection is worth less than its cognitive and operational cost, and its contracts can be preserved through an incremental, reversible change.

Prefer no structural change over speculative flexibility. Prefer a local simplification over a boundary. Prefer a boundary over a system-wide migration. A fashionable name is never evidence.

## Modes and Authorization

Choose one mode in Phase 0 and state it explicitly.

- **Analysis/planning mode — default:** inspect, reconstruct, compare, and produce the `Codebase Design Assessment`. Do not edit implementation files. The migration may identify slices and proof obligations, but ordinary file/symbol-level implementation planning belongs to `plan-with-senior-dev` after the target design is approved.
- **Implementation mode — explicit authorization required:** implement only when the user clearly requests restructuring, not merely assessment or a proposal. Require an approved target design and migration boundary. If material behavior, public contracts, or durable state decisions remain unresolved, return to analysis/planning or hand off to `plan-with-senior-dev` before editing.

In either mode, preserve existing contracts by default. Public APIs, schemas, events, files, CLIs, and user workflows may change only with explicit authorization that names the allowed change.

## Evidence Discipline

Label material claims in working notes and the assessment:

- `[Fact]` — verified in code, tests, configuration, history, runtime evidence, or authoritative documentation; cite `file:line`, command output, or URL.
- `[Inference]` — conclusion drawn from facts; state the reasoning and confidence.
- `[Decision]` — selected design choice and the evidence or constraint that forces it.
- `[Assumption]` — unverified premise; state impact and a way to verify it.

Do not let a blocking assumption survive into an implementation migration. Re-check facts after significant edits or repository changes.

## Reference Routing

- Read `references/design-decision-rubric.md` before Phase 3. Use it for analysis dimensions, simplicity controls, alternative comparison, the 14-question pattern admission test, removal signals, language idioms, and runtime/distributed hazards.
- Read `references/worked-examples.md` before Phase 5 when the problem resembles conditional dispatch, volatile integrations, redundant abstraction stacks, or distributed processing.

## Workflow

Complete Phases 0–10 in order. Earlier conclusions may be revised when later evidence contradicts them.

### Phase 0: Establish Constraints and Authorization

- Restate the observable goal, scope, exclusions, constraints, invariants, and success measures.
- Select analysis/planning or implementation mode.
- Inventory protected contracts: public APIs, schemas, events, files, CLIs, user workflows, persistence, and operational promises.
- Record explicit authorization for any protected-contract change; otherwise mark it invariant.
- Inspect repository guidance and worktree state. In implementation mode, stop before overwriting targeted user changes.

### Phase 1: Reconnaissance

- Identify entry points, modules, packages, deployments, storage, queues, external systems, tests, configuration, and observability on the target path.
- Find local analogues and recently changed hotspots. Use history when it can prove churn or ownership boundaries.
- Trace at least one real request, command, job, or event from input to observable outcome.
- Build an evidence ledger. Do not infer architecture solely from directory names or diagrams.

### Phase 2: Reconstruct the Current State

- Map responsibilities, dependency direction, data and control flow, state ownership, consistency boundaries, failure paths, and deployment units.
- Distinguish intended contracts from accidental coupling.
- Record where behavior is encoded: code, types, tests, configuration, schema, message semantics, ordering, retries, and operator runbooks.
- Describe the current design before judging it. Preserve contradictory evidence rather than smoothing it over.

### Phase 3: Identify Design Pressures

- Use the analysis dimensions in `references/design-decision-rubric.md`.
- Tie each pressure to concrete evidence: repeated change propagation, unstable dependency, ambiguous ownership, defect history, test friction, runtime risk, or team coordination cost.
- Separate symptoms from structural causes. A long file, many classes, or disliked pattern is not a cause by itself.
- Rank pressures by correctness risk, frequency, blast radius, and cost of leaving them unchanged.

### Phase 4: Classify the Change

Choose exactly one minimum sufficient level:

| Level | Meaning | Admission gate |
|---|---|---|
| **L0 — No structural change** | Keep the design; improve evidence, tests, naming, documentation, configuration, or a direct local behavior. | No demonstrated structural cause. |
| **L1 — Local simplification** | Reshape implementation within one cohesive module without changing ownership or a shared boundary. | A local cause exists and can be resolved without new cross-module contracts. |
| **L2 — Boundary redesign** | Add, replace, or remove a boundary between independently changing code, such as an Adapter or explicit port. | Evidence shows volatility, propagation, or ownership pressure across multiple consumers/modules, and L1 cannot contain it. |
| **L3 — Architectural migration** | Change subsystem boundaries, dependency direction, state ownership, consistency model, deployment topology, or public/durable contracts. | Cross-system pressure is proven, L0–L2 are insufficient, operational semantics are defined, and an incremental rollback path exists. |

**Local-to-architecture gate:** never promote a local readability, duplication, testability, or two-branch problem to L2 or L3 without evidence that the cause crosses an independently changing boundary. For L3, prove why a boundary-level design cannot solve the problem and identify the system-level invariant at risk. If the proof is absent, cap the recommendation at L1.

### Phase 5: Generate Alternatives

- Generate at least three serious options: keep/current design with targeted relief, the minimum sufficient redesign, and one credible stronger or differently shaped design.
- Include pattern removal and consolidation when existing indirection is part of the pressure.
- Compare options using the rubric, including behavior preservation, net complexity, operational semantics, migration, rollback, team ownership, and likely future change—not diagram neatness.
- Run the complete 14-question admission test for every introduced or retained pattern. A failed hard question rejects or narrows the pattern.

### Phase 6: Adversarial Review

Attack the leading option with concrete counterexamples:

- Can the pressure be removed with L0 or L1?
- Which current behavior, caller, file format, schema, event, CLI, or workflow could change accidentally?
- Does the design hide a dependency rather than remove coupling?
- Who owns state, retries, idempotency, transactions, ordering, timeouts, cancellation, and partial failure?
- Can old and new paths coexist during deployment? Can operators observe and reverse the change?
- What evidence would make the rejected alternative win?

Repair the design or lower its change level. Do not turn attacks into a generic risk list.

### Phase 7: Define the Target Design

- Assign one responsibility and owner to each component or boundary.
- Specify dependency direction, allowed calls, state ownership, data contracts, failure semantics, and operational ownership.
- Name patterns only after describing the problem they solve and their admitted cost.
- Show what is removed as well as what is added.
- Define invariants and protected contracts in testable terms.

### Phase 8: Design the Incremental Migration

- Split the migration into independently verifiable, reversible slices.
- Prefer branch-by-abstraction, compatibility shims, parallel reads, shadow comparison, or staged caller migration only when their temporary complexity has a named removal point.
- For each slice, state prerequisites, changed boundary, preserved behavior, proof, telemetry, rollback trigger, rollback action, and cleanup condition.
- Avoid unguarded dual writes. When dual operation is unavoidable, define source of truth, reconciliation, idempotency, ordering, and failure recovery.
- Keep the old path until the new path proves the required invariants, unless explicit authorization accepts irreversible cutover risk.

### Phase 9: Validate Design and Implementation

- Define characterization tests before structural edits when current behavior is not already pinned down.
- Validate public contracts, domain behavior, state transitions, failure behavior, performance budgets, security boundaries, and operator workflows.
- In implementation mode, verify after each slice. Stop and narrow or roll back the introduced slice when behavior, compatibility, or operational evidence fails.
- Record raw commands, results, limitations, and residual risks. Do not claim preservation from passing unit tests alone.

### Phase 10: Clean Up and Close

- Remove temporary shims, flags, duplicate paths, dead types, obsolete adapters, stale factories, and migration-only telemetry when their exit criteria are met.
- Update diagrams, ADRs, ownership docs, runbooks, and examples only where the final design makes them stale.
- Confirm no accidental public surface, orphan abstraction, or permanent “temporary” complexity remains.
- Recompute the net complexity and pattern admission decisions against the final state.

## Implementation Safeguards

When implementation is authorized:

- Characterize behavior before restructuring and keep each patch small enough to attribute failures.
- Preserve names, wire shapes, persistence semantics, ordering, errors, side effects, and workflows unless explicitly authorized otherwise.
- Do not combine behavior change, dependency upgrade, performance optimization, or unrelated cleanup with a structural slice.
- Keep rollback executable, not aspirational. Name the last safe state and the evidence that triggers reversal.
- Stop on a material design–repository contradiction. Report the contradiction; do not improvise a broader architecture.
- Never discard unrelated user changes or use destructive repository commands to manufacture a clean state.

## Required Output: Codebase Design Assessment

Produce these 14 sections in this exact order, even when a section concludes “none” with evidence:

1. **Decision Summary** — recommended change level, target, and why it is the minimum sufficient design.
2. **Scope, Authorization, and Constraints** — mode, in/out of scope, protected contracts, explicit permissions, and hard constraints.
3. **Evidence Ledger** — labeled facts, inferences, decisions, assumptions, citations, contradictions, and confidence.
4. **Current-State Reconstruction** — responsibilities, dependency/data/control flow, state ownership, failures, and deployments.
5. **Design Pressures** — ranked structural causes and the evidence connecting each cause to observed cost or risk.
6. **Change Classification** — L0–L3 choice and proof that lower levels are insufficient.
7. **Pattern Decisions** — admission-test result for every introduced, retained, or removed pattern and its net cost.
8. **Alternatives and Rejected Alternatives** — comparison, rejection evidence, and revisit conditions.
9. **Target Design** — components, boundaries, dependency rules, state/contract ownership, failure semantics, and removals.
10. **Behavior and Contract Preservation** — unchanged behavior, characterized gaps, authorized changes, and compatibility rules.
11. **Incremental Migration and Rollback** — ordered slices, coexistence strategy, proof, cutover, rollback triggers/actions, and cleanup gates.
12. **Validation and Operational Analysis** — tests, commands, telemetry, deployment safety, runtime/distributed hazards, and residual proof gaps.
13. **Unchanged Areas** — modules, contracts, data, workflows, and infrastructure intentionally left untouched, with reasons.
14. **Non-Goals and Residual Risks** — excluded work, accepted tradeoffs, remaining uncertainty, owners, and follow-up evidence.

In implementation mode, append a concise change record mapping each edited file and migration slice to its authorization and verification result. Do not replace the assessment with a patch summary.

## Adjacent Skill Boundaries

- Use `codebase-issue-auditor` to discover and prove problems across a repository. This skill starts from a scoped concern or accepted finding and decides whether its cause is structural and what target design, if any, is justified.
- Use `plan-with-senior-dev` after a target design is approved to convert it into a decision-complete file/symbol-level implementation specification. This skill owns structural diagnosis, pattern choice, target boundaries, and migration shape—not ordinary implementation planning.
- Use `optimize-codebase-with-senior-dev` when the primary objective is measurable performance, build/runtime efficiency, dependency/tooling leverage, or ecosystem capability. This skill may consider performance as a constraint but does not invent an architecture to chase unmeasured speed.
- Use `implement-with-senior-dev` to execute an approved, specific implementation plan when design decisions are already settled.
