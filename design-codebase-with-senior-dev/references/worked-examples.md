# Worked Examples

Use these examples as calibration, not templates to copy. Each shows how evidence, change level, pattern cost, migration, and operational semantics shape the decision.

## Contents

1. Reject Strategy for a stable two-branch decision
2. Introduce an Adapter around a volatile SDK
3. Remove a one-interface/one-implementation/one-factory stack
4. Reject a superficially clean distributed split

## 1. Reject Strategy for a Stable Two-Branch Decision

**Scenario:** An invoice formatter chooses `compact` or `detailed` output. A proposal adds `FormatterStrategy`, two implementation classes, a registry, and a factory.

**Evidence**

- `[Fact]` The choice is a closed enum with two variants used in one module.
- `[Fact]` Five years of history show no third format and no independent ownership or deployment boundary.
- `[Fact]` Both branches share validation and differ in a short rendering step.
- `[Inference]` The pressure is local readability, not substitutability or volatile integration.

**Decision:** Classify as **L1 — Local simplification**. Reject Strategy. Keep a direct exhaustive branch, extract only branch-local rendering functions if they clarify the shared flow, and use the language’s closed-union or enum exhaustiveness support.

**Admission result:** The proposed Strategy fails concrete recurring pressure, lower-level exhaustion, stable seam, and net-value questions. It adds four concepts without reducing cross-boundary change.

**Preservation and proof:** Keep accepted inputs, output bytes, validation order, and error messages unchanged. Characterization tests assert exact output for both variants and invalid input. No migration or runtime rollout is needed.

**Revisit when:** formats become externally supplied, independently released, or numerous enough that changes repeatedly collide in the central module.

## 2. Introduce an Adapter Around a Volatile SDK

**Scenario:** Four modules call a payment provider SDK directly. Minor SDK releases repeatedly rename request fields and exception types, forcing coordinated edits and leaking provider errors into domain code.

**Evidence**

- `[Fact]` Four consumers construct provider requests and translate the same three errors differently.
- `[Fact]` Three recent provider upgrades changed all four modules.
- `[Fact]` Domain callers need only `authorize`, `capture`, and `refund`; they do not need the SDK’s full surface.
- `[Inference]` External volatility and inconsistent translation cross independently changing modules; L1 cannot contain the propagation.

**Decision:** Classify as **L2 — Boundary redesign**. Admit a narrow `PaymentGateway` boundary owned by the domain and one provider Adapter that owns SDK construction, request/response translation, timeouts, and provider-error classification. Do not wrap unused SDK methods.

**Why Adapter earns its cost:** It has a named external-volatility seam, multiple real consumers, a contract smaller and more stable than the SDK, explicit failure semantics, and measurable propagation reduction.

**Incremental migration**

1. Characterize current requests, returned domain values, error mapping, logs, and timeout behavior.
2. Add the boundary and Adapter behind one existing consumer; compare provider payloads in tests.
3. Migrate one consumer per slice, keeping direct SDK use available for rollback.
4. After all consumers use the Adapter and production telemetry is stable, remove direct SDK imports and duplicated translation.

**Rollback:** Repoint the migrated consumer to its previous direct call without changing domain contracts. Trigger rollback on payload mismatch, changed error classification, or latency/error-budget regression.

**Operational proof:** Verify retry ownership, idempotency keys, timeout propagation, provider rate limits, correlation IDs, and mixed-version deployment. The Adapter centralizes these semantics; it does not silently invent new retries.

## 3. Remove a One-Interface/One-Implementation/One-Factory Abstraction

**Scenario:** `UserPreferencesRepository` has one implementation, `SqlUserPreferencesRepository`, created only by `UserPreferencesRepositoryFactory`, whose sole method calls the constructor. No plugin or alternate datastore exists.

**Evidence**

- `[Fact]` The interface and factory each have one production consumer path and one implementation.
- `[Fact]` The factory performs no selection, lifecycle, validation, caching, or configuration translation.
- `[Fact]` Tests mock the interface, but integration tests already provide a disposable database.
- `[Fact]` Common schema changes require edits to the interface, implementation, factory fixtures, and mocks in lockstep.
- `[Inference]` The stack hides construction and increases change propagation without protecting a volatile boundary.

**Decision:** Classify as **L1 — Local simplification**. Remove the factory and interface; inject or construct the concrete repository explicitly at the composition root. Keep its public module function/method contract if callers depend on it.

**Removal-rule result:** Current protection is lower than cognitive and maintenance cost. Removal is admissible because state ownership, SQL behavior, transactions, errors, and caller-visible signatures can remain unchanged.

**Incremental migration**

1. Add characterization/integration coverage for queries, transaction participation, missing data, and error mapping.
2. Change one composition path to construct the concrete repository directly while preserving the caller type shape where needed.
3. Replace mock-heavy tests with fakes only where behavior-level integration is impractical; do not weaken coverage.
4. Remove the unused factory, interface, bindings, and fixtures after reference searches and tests prove no runtime discovery path remains.

**Rollback:** Restore the previous binding and types from the last slice. Do not combine the collapse with schema or query changes.

**Revisit when:** a second independently maintained datastore or remote provider becomes a committed requirement and a consumer-owned seam would reduce real propagation.

## 4. Reject a Superficially Clean Distributed Design

**Scenario:** A monolithic order workflow is proposed as three services—Orders, Inventory, and Billing—connected by at-least-once events. The diagram assigns one database per service but does not define duplicate delivery, ordering, or cross-service invariants.

**Evidence**

- `[Fact]` Today, order creation, stock reservation, and payment authorization share one database transaction.
- `[Fact]` The proposal’s broker provides at-least-once delivery and may reorder events across partitions.
- `[Fact]` Payment authorization is externally visible and cannot always be undone synchronously.
- `[Fact]` No service owns the composite invariant “an accepted order has exactly one valid reservation and authorization outcome.”
- `[Inference]` The split converts a known atomic invariant into an undefined distributed protocol.

**Adversarial trace**

1. `OrderCreated` is delivered twice after the consumer commits but before acknowledging.
2. Inventory reserves twice because no durable idempotency key or uniqueness rule is defined.
3. Billing succeeds, but the inventory compensation times out.
4. The Orders service cannot truthfully report accepted, rejected, or pending because ownership and reconciliation are unspecified.

**Decision:** Reject **L3 — Architectural migration**. Keep the workflow in one transactional boundary. If code organization is the concern, use **L1** modules or an in-process **L2** boundary with explicit ownership and no remote semantics.

**Why the distributed pattern fails:** It fails unambiguous state ownership, behavior preservation, operational semantics, incremental reversibility, and net-value gates. Separate deployability is not currently supported by scale, isolation, compliance, or team evidence.

**Revisit when:** independent scaling or deployment is evidenced and the design specifies, tests, and operates:

- an authoritative order state machine and owner;
- stable idempotency keys and deduplication retention;
- partition/ordering rules and stale-event handling;
- transaction/outbox boundaries, retry ownership, and bounded backoff;
- compensation and reconciliation for every partial-failure state;
- mixed-version event compatibility, telemetry, alerts, and operator runbooks;
- a staged migration that shadows or mirrors behavior without unsafe dual writes;
- rollback compatible with data already written by the new protocol.

Until those obligations have owners and proof, the visually clean service split is a correctness regression, not an architecture improvement.
