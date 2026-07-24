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
6. **Material ambiguity reconciliation:** inspect the repository before asking questions. Never ask for a repository-discoverable fact. Ask for user confirmation ONLY when material ambiguity remains that cannot be resolved through repository evidence (such as user-visible behavior, public or shared contracts, persisted state, state ownership, security or authorization, failure semantics, migration and rollback constraints, external effects, or deployment compatibility). When no material ambiguity remains, continue automatically and record the resolved frame in the assessment. Continue automatically without adding a mandatory confirmation pause; do not pause or block an otherwise decision-complete assessment.
7. **Fail-closed finalization:** raw checker passes are not submission-ready. Run `finalize_assessment.py` to produce the final, receipt-stamped output (`<!-- assessment-validation: 2; level: L2; sha256: <hash> -->` or `<!-- assessment-validation: 2; mode: discovery-only; sha256: <hash> -->`).

## Canonical Evidence Records & Specification

Use canonical records throughout the assessment:

- `Decision Summary` — mandatory summary block at the top detailing mode, target, level, recommendation, protected contracts, primary pressure, debt disposition, risk, next owner, and selected design-id.
- `F-n` — verified fact with `path:line` or `git-history:<sha>:<path>:<line>`, anchor, observation, source (`code`, `test`, `fixture`, `configuration`, `schema`, `repository-history`, `runtime`, `production`, `ownership`, `deployment`), strength (`direct`, `corroborated`, `inferred`), and freshness (`current`, `potentially-stale`, `historical`).
  - Repository history facts MUST use the locator format: `git-history:<commit-sha>:<repository-path>:<line>`. Validator checks that repository is a Git checkout, commit exists, file exists at commit, line is within historical file bounds, anchor exists near cited historical line, and path does not escape repository.
- `P-n` — ranked structural pressure citing the facts (`F-n`/`E-n`) that establish its cost or risk.
- `C-n` — protected contract classified as `preserved`, `authorized-change`, or `at-risk`.
- `D-n` — selected L0-L3 decision:
  - Format: `D-1: level: L2 | design-id: payment-gateway-adapter | selected: PaymentGateway interface and ProviderAdapter | because: F-1, P-1 | rejected: L1 does not contain verified cross-module propagation`
  - `design-id` is mandatory, stable, machine-readable identity, and non-placeholder.
  - `because` must include at least one `F-n` or `E-n` AND at least one `P-n`.
  - `rejected` must explain why the nearest weaker option is insufficient.
- `O-n` — serious alternatives:
  - Format: `O-3: level: L2 | design-id: payment-gateway-adapter | selected: yes | concepts: PaymentGateway, ProviderAdapter | argument-for: contains SDK volatility | argument-against: adds one abstraction boundary | revisit: provider SDK becomes stable`
  - Every alternative has a unique `design-id`.
  - The selected alternative's `design-id` equals `D-n.design-id`.
  - Exactly one alternative is selected, and its level equals `D-n.level`.
- `T-n` — autonomous target-discovery candidate records:
  - Format:
    ```text
    T-1:
    target: src/payments/service.py
    evidence: F-1, F-2
    pressure: P-1
    affected: C-1
    confidence: high
    likely-level: L2
    blast-radius: bounded
    product-intent-required: false
    rank: 1
    status: selected
    reason: Direct SDK volatility propagates across four domain callers.
    correctness-risk: medium
    operational-risk: medium
    debt-interest: high
    change-propagation: wide
    state-ambiguity: low
    scope-boundedness: high
    reversibility: high
    structural-confidence: high
    ```
  - Valid Enums:
    - `confidence`: `low | medium | high`
    - `likely-level`: `L0 | L1 | L2 | L3`
    - `product-intent-required`: `true | false`
    - `status`: `selected | rejected | deferred`
    - `correctness-risk`: `low | medium | high`
    - `operational-risk`: `low | medium | high`
    - `debt-interest`: `none | low | medium | high`
    - `change-propagation`: `local | bounded | wide`
    - `state-ambiguity`: `low | medium | high`
    - `scope-boundedness`: `low | medium | high`
    - `reversibility`: `low | medium | high`
    - `structural-confidence`: `low | medium | high`
  - Candidate Score Calculation & Material Tie Threshold:
    Candidate score is computed from ranking enums. In autonomous mode, if `top_score - second_score <= 2.0` (material tie), autonomous selection MUST fail closed and force emission of a `discovery-only` assessment handed off to `codebase-issue-auditor`.
- `G-n` — pattern decision (`admit`, `admit-narrowed`, `retain`, `remove`, `reject`, `defer`) with `scope` (`introduced`, `removed`, `retained`, `rejected`, `deferred`, `relied-upon`) and Q1-Q14 gate answers.
- `TD-n` — structural technical debt record with type (`structural`, `boundary`, `state-ownership`, `dependency`, `migration`, `operational`), principal, interest, frequency (`current`, `recurring`, `historical`, `unknown`), blast radius, disposition (`accept`, `monitor`, `contain`, `repay`, `retire`), reason, repayment boundary, recurrence guard, and revisit trigger.
- `Operational Semantics` — operational fields (`source of truth`, `failures`, `timeouts`, `retries`, `idempotency`, `ordering`, `transactions`, `observability`, `resource limits`). If operational field is not-applicable, structured format is required: `Ordering: not-applicable | evidence: F-1 | reason: Each request is independently processed by one synchronous owner.`
- `V-n` — exact command, test, or manual check and its expected observable result.
- `M-n` — reversible L2/L3 migration slice with prerequisite, changed boundary, preserved contracts (`C-n`), proof verifications (`V-n`), rollback trigger, rollback action, and cleanup with observable completion criteria.
- `R-n` — residual risk with severity, scenario, consequence, owner, and follow-up.
- `H-n` — assessment-only handoff state (`finish assessment`, `plan-with-senior-dev`, `codebase-issue-auditor`, `optimize-codebase-with-senior-dev`, `implement-with-senior-dev`).

## Finalization Receipts

`finalize_assessment.py` stamps one of two finalization receipt formats depending on assessment mode:
- Targeted / Autonomous mode:
  ```text
  <!-- assessment-validation: 2; level: L2; sha256: <digest> -->
  ```
- Discovery-only mode:
  ```text
  <!-- assessment-validation: 2; mode: discovery-only; sha256: <digest> -->
  ```

## Skill Directory Resolution

Execute bundled runtime commands with the active skill directory set as the process working directory:
- Resolve `skill-root` as the directory containing `SKILL.md` and `repo-root` as the absolute target repository path.
- All non-script paths passed as arguments MUST be absolute paths.
- Never write output or state files relative to the installed skill package directory.

## Reference and Tool Routing

1. Read `references/design-decision-rubric.md` before classifying the change. Apply analysis dimensions, target ranking rules, material ambiguity rules, technical-debt dispositions, and evidence matrix.
2. Read `references/worked-examples.md` for reference implementations of Contract v2 assessments.
3. `references/assessment-contract.json` is the executable source of truth for contract v2 sections, enums, weights, and hard gates.
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
   For discovery-only mode:
   ```bash
   python scripts/finalize_assessment.py --level L0 --mode discovery-only --repo-root /absolute/path/to/repository /absolute/path/to/draft_discovery_only.md > /absolute/path/to/final_discovery_only.md
   ```

## Workflow

Complete Gates 1-7 in order.

### Gate 1: Frame and Protect
- Determine invocation mode (Targeted Mode A vs Autonomous Mode B).
- Identify protected behavior and contracts as `C-n` records. Default to `preserved`.
- Record assumptions as `A-n`.

### Gate 2: Discover or Ground the Target
- **Targeted Mode A:** Ground supplied target in repository evidence (`F-n`).
- **Autonomous Mode B:** Perform bounded discovery pass. Generate up to 5 candidate `T-n` records. Rank candidates by scoring enums. Select exactly 1 dominant candidate if top score exceeds second score by $> 2.0$; if tied ($\le 2.0$), emit discovery-only assessment and hand off to `codebase-issue-auditor`.

### Gate 3: Reconcile Material Ambiguity
- Ask the user for clarification ONLY when a material ambiguity remains that cannot be resolved through repository evidence.
- continue automatically without adding a mandatory confirmation pause.
- do not pause or block an otherwise decision-complete assessment.
- do not choose an unresolved product or contract decision on the user's behalf.

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
2. Is that pressure repeated across real change sites, consumers, or a demonstrably volatile external boundary?
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
