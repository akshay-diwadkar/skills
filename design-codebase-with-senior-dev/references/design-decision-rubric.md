# Design Decision Rubric

Use this reference to judge whether structural change is warranted and whether a proposed pattern earns its cost. Apply the parts relevant to the assessed path; apply every section when admitting an architectural migration.

## Contents

1. Analysis dimensions
2. Design principles
3. Simplicity controls
4. Alternative comparison
5. Fourteen-question pattern admission test
6. Pattern-removal signals
7. Language-aware idioms
8. Runtime and distributed-system hazards

## 1. Analysis Dimensions

Evaluate the current and target designs against evidence in each dimension.

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

Do not convert every weak score into a redesign. Rank only pressures linked to a requested outcome, correctness risk, or repeated cost.

## 2. Design Principles

- Preserve observable behavior unless a contract change is explicitly authorized.
- Keep policy independent from mechanisms only where mechanisms demonstrably vary or threaten policy correctness.
- Make state ownership and dependency direction explicit.
- Prefer compile-time or type-level constraints over comments when the language supports them without disproportionate ceremony.
- Keep failure, latency, and consistency semantics visible at boundaries.
- Design for the current scale and proven change horizon; record a revisit trigger for plausible future pressure.
- Reuse local idioms before importing a cross-language pattern vocabulary.
- Make migration and rollback properties of the design, not release-phase afterthoughts.
- Delete superseded paths. A completed migration should usually reduce or contain total concepts.
- Treat tests, telemetry, runbooks, schemas, and deployment compatibility as design artifacts.

## 3. Simplicity Controls

Apply these controls before approving L2 or L3:

1. **Direct-change control:** describe the smallest direct edit that solves the observed problem. Reject a stronger design unless it materially fails a named constraint.
2. **Concept budget:** list every new interface, type, service, mapper, factory, datastore, queue, flag, job, and operational obligation. Every item needs a current payer.
3. **Indirection depth:** walk a common request and change task through the target design. Reject layers that relay without translating, protecting, owning, or enforcing.
4. **Variation proof:** distinguish current variation from hypothetical variation. One implementation and no credible volatility usually do not justify a substitutability abstraction.
5. **Change-horizon control:** optimize for changes evidenced by history, roadmap, contract obligations, or active integrations—not imagined generality.
6. **Reversibility control:** prefer the option that can be introduced, observed, and removed in small slices.
7. **Net-complexity check:** compare concepts removed, concepts added, cross-boundary calls, operational states, and ownership ambiguity. “Cleaner” diagrams do not offset higher total complexity.
8. **Pattern-name delay:** describe responsibilities and forces before assigning a pattern name. If the name is doing the persuasive work, evidence is insufficient.

## 4. Alternative Comparison

Compare at least three options using the same scale. Include “keep the current structure with targeted relief.” Do not weight criteria silently.

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

Record the strongest argument for and against each option. A rejected option needs a concrete rejection reason and a revisit condition.

## 5. Fourteen-Question Pattern Admission Test

Run all 14 questions for every pattern introduced or deliberately retained. Answer `yes`, `no`, or `unknown`, with evidence. Questions 1, 3, 4, 8, 9, 11, 13, and 14 are hard gates: a `no` rejects the pattern; an `unknown` blocks implementation.

1. **Concrete pressure:** Is there a current, evidenced problem or correctness risk that this pattern directly resolves?
2. **Recurrence or volatility:** Is the pressure repeated across real change sites, consumers, or a demonstrably volatile external boundary?
3. **Lower-level exhaustion:** Have L0/L1 alternatives been described and shown insufficient?
4. **Named responsibility:** Does each new abstraction have one precise responsibility and owner?
5. **Stable seam:** Is the abstraction’s contract more stable than the details it hides?
6. **Propagation reduction:** Will a representative future change touch fewer independently owned modules or contracts?
7. **Honest dependencies:** Does the pattern reduce or constrain coupling rather than hide it behind lookup, reflection, factories, or generic containers?
8. **Unambiguous state ownership:** Is the source of truth and authority for each affected state explicit?
9. **Behavior preservation:** Are protected APIs, schemas, events, files, CLIs, errors, side effects, and workflows characterized and preserved or explicitly authorized to change?
10. **Test and observability seam:** Can the pattern be verified through behavior and observed in production without mocks or telemetry that merely mirror internals?
11. **Operational semantics:** Are timeouts, cancellation, retries, idempotency, ordering, transactions, partial failure, and resource limits defined where applicable?
12. **Repository and language fit:** Does the design use local and language-native idioms, or justify the new vocabulary it adds?
13. **Incremental reversibility:** Can it be introduced in independently verifiable slices with explicit rollback triggers and actions?
14. **Net value:** Over the evidenced change horizon, do avoided risk and change cost exceed cognitive, runtime, operational, migration, and ownership costs?

For a `no` on a non-hard question, either narrow the pattern until it becomes `yes` or record why the weakness is acceptable under an explicit constraint. Count alone never admits a pattern.

## 6. Pattern-Removal Signals

Investigate removal or collapse when evidence shows one or more of these signals:

- one interface, one implementation, and one factory with no credible substitution or boundary volatility;
- a pass-through service, repository, facade, mapper, or controller that owns no policy, translation, protection, or lifecycle;
- an abstraction used only to make unit-test mocks possible while integration behavior remains untested;
- generic registries, service locators, or reflection that hide dependencies and construction ownership;
- parallel domain models whose mappings carry no boundary meaning and change in lockstep;
- Strategy, Visitor, Builder, Command, or plugin machinery serving a stable closed set better expressed by a direct branch or native data structure;
- factories that only call constructors and add no selection, lifecycle, validation, or compatibility logic;
- feature flags, compatibility shims, or dual paths past their exit criteria;
- wrappers that expose nearly the entire underlying SDK and therefore fail to protect consumers from volatility;
- base classes with no shared invariant, or subclasses that override most behavior;
- abstraction churn where common changes require editing both the abstraction and every implementation;
- ownership ambiguity caused by two layers believing the other owns validation, retries, caching, transactions, or cleanup.

Removal still pays migration cost. Before collapsing a layer, find external consumers, reflection/config references, serialized type names, test fixtures, lifecycle hooks, and operational behavior. Characterize the preserved contract and remove in reversible slices.

## 7. Language-Aware Idioms

Prefer the repository’s established idiom. When no local precedent resolves the choice, use the language’s simplest native mechanism:

- **Python:** prefer modules, functions, protocols for genuine structural typing, context managers for lifecycle, dataclasses/typed models for data, and explicit dependency construction. Avoid Java-style interface/factory stacks around one implementation.
- **TypeScript/JavaScript:** prefer structural interfaces only at real boundaries, discriminated unions for closed variants, plain functions/objects for local policy, and explicit imports/construction. Account for runtime schema validation where types disappear.
- **Java/Kotlin/C#:** use interfaces at independently varying or externally owned seams, sealed types for closed variants, records/data classes for values, and framework DI only when the repository already accepts its lifecycle and discovery costs.
- **Go:** prefer small consumer-owned interfaces, concrete return types, explicit constructors, and composition. Avoid provider-owned “interface for every struct” and package cycles disguised by broad interfaces.
- **Rust:** use enums for closed alternatives, traits for real generic/substitution needs, ownership and lifetimes to express state authority, and explicit error types. Avoid dynamic dispatch where static composition suffices.
- **Functional languages:** prefer algebraic data types, pure functions, modules, and effect boundaries native to the ecosystem. Do not translate object-pattern catalogs mechanically.

Framework annotations, containers, code generation, macros, and reflection add hidden construction and runtime semantics. Admit them only after inventorying how the repository builds, tests, debugs, and deploys them.

## 8. Runtime and Distributed-System Hazards

A structurally elegant diagram can still be operationally incorrect. For every process, thread, service, queue, datastore, cache, or external boundary, examine:

- **Delivery semantics:** at-most-once, at-least-once, or effectively-once; duplicate detection and retention window.
- **Idempotency:** key selection, scope, persistence, replay behavior, and side effects that cannot be repeated safely.
- **Ordering:** partition keys, concurrency, reordering tolerance, stale writes, sequence/version checks.
- **Transactions:** atomic invariant, transaction boundary, isolation, locks, sagas/compensation, outbox/inbox, and dual-write failure.
- **Retries:** retryable error classification, ownership, budget, backoff, jitter, amplification, poison messages, and dead-letter handling.
- **Timeouts and cancellation:** end-to-end deadline propagation, abandoned work, cleanup, and resource leakage.
- **Partial failure:** recovery after some effects commit, reconciliation, operator intervention, and truthful client response.
- **Backpressure and capacity:** bounded queues, admission control, fan-out, memory, connection pools, thread/task limits, and load shedding.
- **Consistency and caches:** source of truth, invalidation, staleness budget, read-your-writes needs, and recovery after cache loss.
- **Schema/event evolution:** backward/forward compatibility, mixed-version deployment, unknown fields, replay of old data, and consumer lag.
- **Time and identity:** clock skew, monotonic versus wall time, globally unique IDs, tenancy, and deduplication scope.
- **Observability:** correlation IDs, attempt counts, state transitions, latency, queue depth, reconciliation drift, and actionable alerts.
- **Deployment and rollback:** mixed versions, database expand/contract, feature-flag consistency, irreversible writes, and rollback compatibility.
- **Security:** trust boundaries, authentication context propagation, authorization at the owning boundary, secret handling, and auditability.

Reject a distributed split when it creates unresolved retry, idempotency, transaction, ordering, or ownership ambiguity. If a process boundary is not required by scale, isolation, deployment, compliance, or ownership evidence, prefer an in-process boundary that preserves the option to split later.
