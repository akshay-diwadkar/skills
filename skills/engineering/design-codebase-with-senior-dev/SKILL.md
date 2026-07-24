---
name: design-codebase-with-senior-dev
description: Assess whether architectural change is justified and choose the smallest evidence-backed design, with an incremental behavior-preserving migration path. Use for boundary, dependency-direction, or state-ownership redesign, design-pattern evaluation or removal, structural technical-debt analysis, and subsystem restructuring. Assessment-only — produces no code; route approved designs to plan-with-senior-dev.
metadata:
  design-contract: "2"
  finalizer: "scripts/finalize_assessment.py"
  validation-required: "true"
---

# Design Codebase With Senior Dev

Determine whether the codebase needs a structural change at all. Reconstruct the current design from repository evidence, expose the forces that make it costly or unsafe, analyze structural technical debt, and choose the least powerful design that resolves those forces without silently changing behavior.

This skill is **assessment-only**. Inspect and run non-mutating checks, but never edit implementation files. Finish with a validated, receipt-stamped `Codebase Design Assessment` emitted through `finalize_assessment.py` and a deterministic handoff.

## Invocation Modes

### Mode A: Targeted Design Assessment
Use this mode when the user supplies a specific target: a module, subsystem, file set, dependency boundary, architectural concern, technical-debt concern, proposed pattern, migration, or requested structural change. Assess the supplied target without broadening into an unrelated repository audit.

### Mode B: Autonomous Target Discovery
Use this mode when the user asks for architectural improvement or design assessment but does not identify a specific target, pain point, module, or subsystem. In this mode, perform a bounded, read-only discovery pass to select one defensible structural concern for assessment. Do not stop or ask the user to choose a target when repository evidence can safely do so.

## Non-Negotiables

1. **Admission rule:** introduce or retain an in-scope pattern only when current, evidenced change pressure or correctness risk repays its indirection, concepts, runtime behavior, migration cost, and long-term ownership.
2. **Removal rule:** remove an in-scope pattern only when its present protection is worth less than its cognitive and operational cost, and its contracts can be preserved through an incremental, reversible migration.
3. Preserve public APIs, schemas, events, files, CLIs, persistence, errors, side effects, user workflows, and operational promises unless explicit authorization names the permitted change.
4. Prefer L0 over L1, L1 over L2, and L2 over L3 whenever the lower level satisfies the evidenced constraints.
5. A fashionable pattern name, long file, large class, duplicate branch, disliked abstraction, or clean diagram is never sufficient evidence by itself.
6. **Material ambiguity reconciliation:** inspect the repository before asking questions. Never ask for a repository-discoverable fact. Ask for user confirmation ONLY when material ambiguity remains that cannot be resolved through repository evidence (such as user-visible behavior, public or shared contracts, persisted state, state ownership, security or authorization, failure semantics, migration and rollback constraints, external effects, or deployment compatibility). When no material ambiguity remains, continue automatically and record the resolved frame in the assessment.
7. **Fail-closed finalization:** raw checker passes are not submission-ready. Run `finalize_assessment.py` to produce the final, receipt-stamped output (`<!-- assessment-validation: 2; sha256: <hash> -->`).

## Evidence Records

Use canonical records throughout the assessment:

- `Decision Summary` — mandatory summary block at the top detailing mode, target, level, recommendation, protected contracts, primary pressure, debt disposition, risk, and next owner.
- `F-n` — verified fact with `path:line`, anchor, observation, source (`code`, `test`, `schema`, `history`, `runtime`, `deployment`), strength (`direct`, `corroborated`, `inferred`), and freshness (`current`, `potentially-stale`).
- `P-n` — ranked structural pressure citing the facts that establish its cost or risk.
- `C-n` — protected contract classified as `preserved`, `authorized-change`, or `at-risk`.
- `D-n` — selected L0-L3 decision, cited reasons, and nearest rejected level or option.
- `A-n` — assumption with status, impact, and verification path.
- `O-n` — serious alternative with level, concept cost, strongest arguments, and revisit trigger.
- `G-n` — pattern decision (`admit`, `admit-narrowed`, `retain`, `remove`, `reject`, `defer`) with Q1-Q14 gate answers and cited evidence.
- `TD-n` — structural technical debt record with type, principal, interest, frequency, blast radius, disposition (`accept`, `monitor`, `contain`, `repay`, `retire`), reason, repayment boundary, recurrence guard, and revisit trigger.
- `T-n` — autonomous target-discovery candidate record (used in Mode B) with target, evidence, pressure, affected contracts, confidence, likely level, blast radius, product-intent dependency, status (`selected`, `rejected`, `deferred`), and reason.
- `V-n` — exact command, test, or manual check and its expected observable result.
- `M-n` — reversible L2/L3 migration slice with proof, rollback trigger, rollback action, and cleanup.
- `R-n` — residual risk with severity, scenario, consequence, owner, and follow-up.
- `H-n` — assessment-only handoff state (`finish assessment`, `plan-with-senior-dev`, `codebase-issue-auditor`, `optimize-codebase-with-senior-dev`, `implement-with-senior-dev`).

## Skill Directory Resolution

Execute bundled runtime commands with the active skill directory (the directory containing this `SKILL.md`) set as the process working directory:
- Resolve `skill-root` as the directory containing `SKILL.md` and `repo-root` as the absolute target repository path.
- All non-script paths passed as arguments MUST be absolute paths.
- Never write output or state files relative to the installed skill package directory.

## Reference and Tool Routing

1. Read `references/design-decision-rubric.md` before classifying the change. Apply analysis dimensions, target ranking rules, material ambiguity rules, technical-debt dispositions, and evidence matrix.
2. Read `references/worked-examples.md` for reference implementations of Contract v2 assessments.
3. `references/assessment-contract.json` is the executable source of truth for contract v2 sections and hard gates.
4. Scaffold matching structure:
   ```bash
   python scripts/scaffold_assessment.py --level L0|L1|L2|L3 [--mode targeted|autonomous-discovery|discovery-only]
   ```
5. Check draft assessment:
   ```bash
   python scripts/check_assessment.py --level <L0|L1|L2|L3> --repo-root /absolute/path/to/repository /absolute/path/to/assessment.md
   ```
6. Finalize assessment (mandatory submission path):
   ```bash
   python scripts/finalize_assessment.py --level <L0|L1|L2|L3> --repo-root /absolute/path/to/repository /absolute/path/to/draft_assessment.md > /absolute/path/to/final_assessment.md
   ```

## Workflow

Complete Gates 1-7 in order.

### Gate 1: Frame and Protect
- Determine invocation mode (Targeted Mode A vs Autonomous Mode B).
- Identify protected behavior and contracts as `C-n` records. Default to `preserved`.
- Record assumptions as `A-n`.

### Gate 2: Discover or Ground the Target
- **Targeted Mode A:** Ground supplied target in repository evidence (`F-n`).
- **Autonomous Mode B:** Perform bounded discovery pass. Generate up to 5 candidate `T-n` records. Rank candidates by correctness risk, operational risk, evidence strength, debt interest, change propagation, state ambiguity, blast radius, bounded scope feasibility, reversibility, and structural confidence. Select exactly 1 dominant candidate if safe; otherwise emit discovery-only assessment and hand off to `codebase-issue-auditor`.

### Gate 3: Reconcile Material Ambiguity
- Ask the user for clarification ONLY when a material ambiguity remains that cannot be resolved through repository evidence.
- When no material ambiguity remains, continue automatically without adding a mandatory confirmation pause; do not pause or block an otherwise decision-complete assessment.
- If an unresolved material ambiguity remains unanswered, pause with the exact unresolved question; do not choose an unresolved product or contract decision on the user's behalf.

### Gate 4: Diagnose Pressures and Technical Debt
- Establish structural pressures (`P-n`) and technical debt (`TD-n`).
- Classify technical debt disposition: `accept`, `monitor`, `contain`, `repay`, or `retire`.
- Require a recurrence guard for `repay`/`retire` and a revisit trigger for `accept`/`monitor`/`contain`.

### Gate 5: Classify Level and Evaluate Patterns
- Classify minimum sufficient level: L0 (Preserve Structure), L1 (Local Simplification), L2 (Boundary Redesign), L3 (Architectural Migration).
- Require L3 evidence across at least 3 independent categories (`code`, `test`, `deployment`, `schema`, `history`, etc.).
- Evaluate pattern decisions (`G-n`) using Q1-Q14 questions. Enforce hard gates (Q1, Q3, Q4, Q8, Q9, Q11, Q13, Q14).

### Gate 6: Define Level-Specific Assessment
- Complete required sections for selected level.
- Include reversible `M-n` migration slices and `V-n` verification checks.
- Do not write symbol-level implementation code.

### Gate 7: Finalize and Handoff
- Run `finalize_assessment.py`.
- Select exactly one handoff state (`H-n`): `finish assessment`, `plan-with-senior-dev`, `codebase-issue-auditor`, `optimize-codebase-with-senior-dev`, or `implement-with-senior-dev`.

## External Research Guidance

1. Ground local architecture and dependency versions first.
2. Research externally only when a decision depends on current framework/API capabilities, deployment mechanics, or platform limits.
3. Prefer official, primary, version-matched sources.
4. Keep local facts (`F-n`) and externally verified facts (`E-n`) distinct.

## Pattern Admission Questions (Q1-Q14)

1. Does it resolve a current evidenced pressure or correctness risk? *(Hard Gate)*
2. Is that pressure recurrent or tied to a demonstrably volatile boundary?
3. Are lower-level alternatives described and insufficient? *(Hard Gate)*
4. Does each abstraction have one precise responsibility and owner? *(Hard Gate)*
5. Is its contract more stable than the details it hides?
6. Does it reduce propagation across independently changing modules?
7. Does it constrain rather than hide dependencies?
8. Is affected state ownership unambiguous? *(Hard Gate)*
9. Are protected contracts preserved or explicitly authorized to change? *(Hard Gate)*
10. Can behavior and production outcomes be verified without mock-only proof?
11. Are applicable operational semantics explicit? *(Hard Gate)*
12. Does it fit repository and language idioms?
13. Can it be introduced in independently verifiable, reversible slices? *(Hard Gate)*
14. Does evidenced value exceed cognitive, runtime, operational, migration, and ownership cost? *(Hard Gate)*

## Handoff Boundaries

- Use `codebase-issue-auditor` when broad repository triage, repository-wide debt inventory, or unselected discovery requires prioritization.
- Use `plan-with-senior-dev` after a target design is approved to produce a file/symbol-level specification.
- Use `optimize-codebase-with-senior-dev` when the primary issue is measured performance or tooling efficiency.
- Use `implement-with-senior-dev` ONLY when an approved decision-complete plan already exists.
