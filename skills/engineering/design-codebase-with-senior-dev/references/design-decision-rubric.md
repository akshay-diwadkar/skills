# Design Decision Rubric

Use this reference to judge whether structural change is warranted and whether an in-scope pattern earns its cost. Apply the parts relevant to L0-L2; apply every section when admitting L3.

## Contents

0. Request-to-evidence alignment & Material Ambiguity
1. Autonomous Target Discovery (Mode B)
2. Structural Technical-Debt Framework
3. Evidence Source, Strength, and Freshness
4. Analysis dimensions
5. Design principles
6. Simplicity controls
7. Alternative comparison
8. Fourteen-question pattern admission test
9. Pattern-removal signals
10. Language-aware idioms
11. Runtime and distributed-system hazards

## 0. Request-to-Evidence Alignment & Material Ambiguity

After grounding the current design, maintain a temporary ledger:

`request statement | repository evidence | design consequence | options | recommendation and reason | answer | status`

Record requested patterns or boundaries unsupported by current pressure, missing intent, scope mismatches, hidden protected contracts, ambiguous ownership, undefined failure semantics, migration constraints, and acceptance gaps.

### Material Ambiguity Reconciliation
Inspect the repository before asking questions. Never ask for a repository-discoverable fact. Ask the user for confirmation ONLY when a material ambiguity remains that cannot be resolved through repository evidence (such as user-visible behavior, public or shared contracts, persisted state, state ownership, security/authorization, failure semantics, migration/rollback constraints, external effects, or deployment compatibility). When no material ambiguity remains, proceed automatically without a mandatory confirmation pause and record the resolved frame in the assessment.
- user-visible or observable behavior;
- public or shared contracts;
- durable or persisted state;
- authoritative state ownership;
- security or authorization boundaries;
- failure semantics;
- deployment topology or compatibility;
- irreversible migration paths;
- rollback behavior;
- legal or compliance obligations;
- admissible L0–L3 classification level.

Ask up to three related blocking questions per round. State the request and cited `F-n` evidence, explain the affected design decision, offer two to four mutually exclusive options when feasible, and identify the recommended option based on admission rules, lower-level sufficiency, repository idioms, contract preservation, and reversibility. When no material ambiguity remains, proceed automatically without a confirmation pause and record the resolved frame in the assessment.

Translate confirmed or resolved outcomes into existing `P-n`, `C-n`, `D-n`, and `A-n` records and discard the ledger.

## 1. Autonomous Target Discovery (Mode B)

When the user asks for architectural improvement without naming a specific target, perform a bounded discovery pass.

### 1.1 Candidate Generation
Search repository entry points, module boundaries, dependency direction, contracts, state ownership, schemas, tests, deployment configs, ownership metadata, and recent change history for high-signal structural pressures. Generate no more than five internal candidate concerns (`T-n` records).

### 1.2 High-Signal Structural Pressures
- Change propagation across multiple modules for one conceptual edit.
- Unclear, duplicated, or conflicting state or contract ownership.
- Dependency cycles or reversed dependency direction.
- Multiple parallel implementations of the same responsibility.
- Redundant 1-interface/1-implementation/factory stacks.
- Obsolete shims, adapters, feature flags, or migration paths.
- Leaked persistence, transport, or deployment details across boundaries.
- Shared mutable state without a clear owner.
- Test fragility caused by unstable boundaries.
- Distributed/async workflows lacking idempotency, reconciliation, or ownership.

### 1.3 Candidate Ranking Criteria
Rank candidates using:
1. Correctness and contract risk.
2. Operational and migration risk.
3. Strength of direct repository evidence.
4. Recurring technical-debt interest.
5. Repeated change propagation.
6. State or ownership ambiguity.
7. Blast radius.
8. Bounded scope feasibility.
9. Reversibility of likely intervention.
10. Confidence that the issue is structural rather than stylistic.

### 1.4 Autonomous Selection Rules
Proceed autonomously with the highest-ranked candidate when all of the following are true:
- It has direct or corroborated repository evidence (`F-n`).
- Its scope can be bounded to one coherent responsibility, boundary, or invariant.
- It materially outranks remaining candidates.
- Assessing it does not require guessing product intent (`product-intent-required: false`).
- Protected behavior and contracts can be identified (`C-n`).
- The assessment remains read-only.
- The likely recommendation remains incremental and reversible.
- The discovery does not require a repository-wide debt inventory.

Record in the final assessment: candidate ranking rationale, why the selected target outranked alternatives, and why it is safe to assess without user confirmation.

### 1.5 Tie-Breaking
When candidates rank similarly, prefer: 1) greater correctness/state/security risk, 2) smaller coherent scope, 3) more reversible intervention, 4) stronger direct evidence, 5) fewer assumptions.

### 1.6 When Not to Select a Target (Discovery-Only Mode)
Do not force a target when evidence is weak, product intent is required, or broad repository triage is needed. Emit a discovery-only assessment with ranked `T-n` records and hand off to `codebase-issue-auditor`.

## 2. Structural Technical-Debt Framework

Structural technical debt is quantified through `TD-n` records:

| Field | Definition | Valid Values / Examples |
|---|---|---|
| `type` | Nature of structural debt | `structural`, `boundary`, `state-ownership`, `dependency`, `migration`, `operational` |
| `evidence` | Repository fact citations | `F-1, F-2` |
| `principal` | Original shortcut, deferred design, or obsolete requirement | `Pass-through repository layer added for mock tests in v1` |
| `interest` | Evidenced recurring cost | `Change propagation across 4 files for every new query` |
| `frequency` | Evidenced occurrence frequency | `current`, `recurring`, `historical`, `unknown` |
| `blast-radius` | Affected components and contracts | `payment gateway module, orders schema` |
| `disposition` | Decision on debt | `accept`, `monitor`, `contain`, `repay`, `retire` |
| `reason` | Why disposition beats alternatives | `Repayment removes 3-file change propagation for new payment methods` |
| `repayment-boundary` | Smallest complete structural change | `Local module simplification (L1)` |
| `recurrence-guard` | Gate preventing re-introduction | `Contract lint rule / unit test checking direct imports` |
| `revisit-trigger` | Measurable future condition | `Adding second payment gateway provider` |

### Debt Dispositions:
- `accept`: Repayment cost exceeds expected interest; require measurable revisit trigger.
- `monitor`: Interest is plausible but not yet evidenced strongly enough; require measurable revisit trigger.
- `contain`: Eliminating debt is unsafe, too broad, or unjustified; bound its blast radius; require revisit trigger.
- `repay`: Bounded structural change removes recurring interest; require recurrence guard.
- `retire`: Remove obsolete shims, flags, dual paths, adapters after exit criteria met; require recurrence guard.

Unattractive, old, or complex code is NOT automatically technical debt. Debt requires evidenced current or near-term interest.

## 3. Evidence Source, Strength, and Freshness

Every `F-n` fact is categorized across three axes:

### Source Categories
- `code` — direct implementation source.
- `test` — unit, integration, or end-to-end test suite.
- `fixture` — static data, mocks, serialized payload.
- `configuration` — deployment, build, environment config.
- `schema` — database migration, OpenAPI, protobuf, GraphQL schema.
- `repository-history` — Git commit history, release notes.
- `runtime` / `production` — execution logs, metrics, telemetry.
- `ownership` — CODEOWNERS, package manifest, team boundary.
- `deployment` — Docker, Kubernetes, CI/CD pipeline.
- `official-external-documentation` — framework or library docs.

### Evidence Strength
- `direct` — explicit line-by-line evidence.
- `corroborated` — supported by multiple independent files/sources.
- `inferred` — logical conclusion requiring verification.

### Freshness
- `current` — matches active HEAD checkout.
- `potentially-stale` — documentation or historical commit that may differ from current code.
- `historical` — past commit or retired branch context.

### Proportional Evidence Requirements
- **L0 & L1:** Supported primarily by direct `code`, `test`, `configuration`, or `fixture` evidence.
- **L2:** Requires evidence of real boundary pressure (multiple consumers, change propagation, external contract, independent dependency).
- **L3:** Requires evidence from at least 3 independent categories (e.g., `code` + `state`/`schema` + `deployment`/`runtime`).

## 4. Analysis Dimensions

Evaluate current and target designs against evidence in each dimension:

| Dimension | Questions to answer | Useful evidence |
|---|---|---|
| Responsibility and cohesion | Does each unit have a coherent reason to change? Are unrelated policies forced through one owner? | change history, imports, call paths, tests |
| Coupling and dependency direction | Which components know about which details? Do stable policies depend on volatile mechanisms? | dependency graph, imports, constructors, build graph |
| Boundary quality | Does the boundary express a real ownership or volatility seam, or merely relay calls? | consumers, change cadence, data translation, deploy ownership |
| State ownership | Is there exactly one authoritative owner for each durable or mutable fact? | schemas, writes, caches, events, reconciliation jobs |
| Consistency and transactions | Which invariants must be atomic? Where can partial work escape? | transactions, queues, retries, failure tests, runbooks |
| Change propagation | How many modules, teams, tests, and deployments change for one requirement? | representative commits, duplicated edits, release steps |
| Contract clarity | Are public, internal, wire, file, CLI, and event contracts explicit and versioned where necessary? | types, schemas, fixtures, compatibility tests |
| Test seams | Can behavior be verified at the right boundary without mocks that reproduce implementation details? | test pyramid, fixtures, mock graph, characterization gaps |
| Failure semantics | Are error categories, timeouts, cancellation, retryability, and degradation visible to callers? | error types, logs, metrics, traces, incident evidence |
| Operational ownership | Can operators observe, deploy, roll back, and recover each component? | telemetry, alerts, rollout config, runbooks, SLOs |
| Security and trust | Where do identity, authorization, secrets, and untrusted data cross boundaries? | auth middleware, threat model, validation, audit logs |
| Performance and resources | Does the design add remote hops, serialization, queues, locks, memory, or unbounded work? | profiles, load tests, capacity limits, query plans |
| Delivery and team topology | Does the boundary align with independently owned and released work, or create coordination tax? | CODEOWNERS, deployment units, review history |
| Cognitive load and evolvability | How many concepts must a maintainer understand to make a common change safely? | onboarding path, indirection depth, common change walkthrough |

## 5. Design Principles

- Preserve observable behavior unless a contract change is explicitly authorized.
- Keep policy independent from mechanisms only where mechanisms demonstrably vary or threaten policy correctness.
- Make state ownership and dependency direction explicit.
- Prefer compile-time or type-level constraints over comments when the language supports them without disproportionate ceremony.
- Keep failure, latency, and consistency semantics visible at boundaries.
- Design for current scale and proven change horizon; record a revisit trigger for plausible future pressure.
- Reuse local idioms before importing a cross-language pattern vocabulary.
- Make migration and rollback properties of the design, not release-phase afterthoughts.
- Delete superseded paths. A completed migration should usually reduce total concepts.
- Treat tests, telemetry, runbooks, schemas, and deployment compatibility as design artifacts.

## 6. Simplicity Controls

Apply direct-change, concept-budget, and reversibility controls at every level. Apply all controls before approving L2 or L3:

1. **Direct-change control:** describe the smallest direct edit that solves the observed problem. Reject a stronger design unless it materially fails a named constraint.
2. **Concept budget:** list every new interface, type, service, mapper, factory, datastore, queue, flag, job, and operational obligation. Every item needs a current payer.
3. **Indirection depth:** walk a common request and change task through the target design. Reject layers that relay without translating, protecting, owning, or enforcing.
4. **Variation proof:** distinguish current variation from hypothetical variation. One implementation and no credible volatility usually do not justify a substitutability abstraction.
5. **Change-horizon control:** optimize for changes evidenced by history, roadmap, contract obligations, or active integrations—not imagined generality.
6. **Reversibility control:** prefer the option that can be introduced, observed, and removed in small slices.
7. **Net-complexity check:** compare concepts removed, concepts added, cross-boundary calls, operational states, and ownership ambiguity.
8. **Pattern-name delay:** describe responsibilities and forces before assigning a pattern name.

## 7. Alternative Comparison

Compare at least three options using the same scale. Include “keep the current structure with targeted relief.”

| Criterion | What a strong option demonstrates |
|---|---|
| Pressure fit | Resolves the ranked structural cause rather than its surface symptom. |
| Change level | Uses the lowest L0–L3 level that satisfies constraints. |
| Behavior safety | Preserves protected contracts and identifies every authorized exception. |
| Net complexity | Removes or contains more burden than it introduces over the evidenced horizon. |
| Dependency and ownership | Improves direction and makes responsibility/state ownership unambiguous. |
| Operational correctness | Defines failures, latency, retries, ordering, consistency, observability, and recovery. |
| Migration safety | Supports independently verifiable slices, coexistence where needed, and executable rollback. |
| Language/repository fit | Uses native and local idioms that maintainers already understand. |
| Testability | Enables behavior-level proof without replacing real semantics with mocks. |
| Performance/security | Meets measured budgets and preserves or strengthens trust boundaries. |
| Team fit | Matches real ownership and release units without unnecessary coordination. |
| Revisitability | States evidence that would change the decision and avoids foreclosing later options. |

## 8. Fourteen-Question Pattern Admission Test

Run all 14 questions only for every pattern materially introduced, removed, or deliberately relied upon by the scoped decision. Answer `yes`, `no`, or `unknown` with evidence. Questions 1, 3, 4, 8, 9, 11, 13, and 14 are hard gates: `no` rejects the pattern; `unknown` blocks design approval.

1. **Concrete pressure:** Is there a current, evidenced problem or correctness risk that this pattern directly resolves? *(Hard Gate)*
2. **Recurrence or volatility:** Is the pressure repeated across real change sites, consumers, or a demonstrably volatile external boundary?
3. **Lower-level exhaustion:** Have L0/L1 alternatives been described and shown insufficient? *(Hard Gate)*
4. **Named responsibility:** Does each new abstraction have one precise responsibility and owner? *(Hard Gate)*
5. **Stable seam:** Is the abstraction’s contract more stable than the details it hides?
6. **Propagation reduction:** Will a representative future change touch fewer independently owned modules or contracts?
7. **Honest dependencies:** Does the pattern reduce or constrain coupling rather than hide it behind lookup, reflection, factories, or generic containers?
8. **Unambiguous state ownership:** Is the source of truth and authority for each affected state explicit? *(Hard Gate)*
9. **Behavior preservation:** Are protected APIs, schemas, events, files, CLIs, errors, side effects, and workflows characterized and preserved or explicitly authorized to change? *(Hard Gate)*
10. **Test and observability seam:** Can the pattern be verified through behavior and observed in production without mocks or telemetry that merely mirror internals?
11. **Operational semantics:** Are timeouts, cancellation, retries, idempotency, ordering, transactions, partial failure, and resource limits defined where applicable? *(Hard Gate)*
12. **Repository and language fit:** Does the design use local and language-native idioms, or justify the new vocabulary it adds?
13. **Incremental reversibility:** Can it be introduced in independently verifiable slices with explicit rollback triggers and actions? *(Hard Gate)*
14. **Net value:** Over the evidenced change horizon, do avoided risk and change cost exceed cognitive, runtime, operational, migration, and ownership costs? *(Hard Gate)*

## 9. Pattern-Removal Signals

Investigate removal or collapse when evidence shows:
- one interface, one implementation, and one factory with no substitution;
- pass-through service, repository, facade, or controller owning no policy or translation;
- abstraction used only for mock tests;
- generic registries or service locators hiding construction ownership;
- parallel models changing in lockstep;
- obsolete feature flags, compatibility shims, or migration paths past exit criteria;
- wrappers exposing the underlying SDK without protecting consumers from volatility.

Characterize preserved contracts (`C-n`) and remove in reversible slices (`M-n`).

## 10. Language-Aware Idioms

- **Python:** Modules, functions, Protocols, dataclasses. Avoid Java-style interface/factory stacks around 1 implementation.
- **TypeScript:** Structural interfaces at real boundaries, discriminated unions, plain functions.
- **Java/Kotlin/C#:** Interfaces at volatile boundaries, sealed types, records/data classes.
- **Go:** Small consumer-owned interfaces, concrete return types, explicit constructors. Avoid interface-per-struct.
- **Rust:** Enums for closed variants, traits for generic/substitution needs, ownership/lifetimes for state authority.

## 11. Runtime and Distributed-System Hazards

For every process, queue, datastore, cache, or external boundary, examine:
- Delivery semantics & Idempotency
- Ordering & Partition keys
- Transactions & Dual-write failures
- Retries, Backoff, Jitter, & Poison messages
- Timeouts, Cancellation, & Resource limits
- Partial failure & Reconciliation
- Schema & Event evolution
- Mixed-version deployment & Rollback compatibility
