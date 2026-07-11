# Ecosystem Leverage

Use this reference after the optimization target is known and a relevant framework, package, runtime, database, build/test tool, CI system, or deployment platform is present. Local evidence selects what to research; ecosystem research does not create an optimization target.

## Contents

- Ecosystem inventory
- Capability matrix
- Evidence order
- Dependency rules
- Optimization passes
- Compatibility and operational gates

## Ecosystem Inventory

Inventory only components that can affect the target:

- language and runtime versions from version files, manifests, containers, CI, and deployment config;
- application frameworks, routers, renderers, ORMs, clients, state/data libraries, and major integrations;
- direct production dependencies, development dependencies, workspace packages, plugins, and lockfile-resolved versions;
- compiler, bundler, task runner, linter, type checker, formatter, test runner, coverage, browser, and fixture tooling;
- database, cache, queue, storage, observability, container, hosting, serverless/edge, and CI/CD platforms;
- configuration, feature flags, execution modes, adapters, and environment-specific overrides.

For each relevant component classify:

- **declared**: present in a manifest or workspace definition;
- **resolved**: exact version or source confirmed from the lockfile or installed metadata;
- **configured**: local config changes its behavior;
- **actively used**: imported, invoked, or exercised on the target path;
- **duplicated**: custom code overlaps a supported capability;
- **transitive-only**: available only through another dependency and not owned as a direct contract.

Do not infer active use from installation alone. Trace imports, scripts, config references, generated output, and the target execution path.

## Capability Matrix

Record one row per plausible capability:

| Field | Required evidence |
| --- | --- |
| Component | Framework/package/tool and resolved version |
| Current use | Relevant imports, config, scripts, or runtime path |
| Native capability | Exact feature, option, API, or mode |
| Target link | How it addresses the measured leverage point |
| Local support | Types, source, metadata, bundled docs, tests, or config schema |
| Official support | Version-matched official docs, release notes, or migration guide |
| Adoption type | Configure, adopt, replace custom code, add, or upgrade |
| Compatibility | Runtime, plugins, deployment, API, and data constraints |
| Costs | Bundle/runtime resources, operations, security, maintenance, and complexity |
| Verification | Before/after metric and behavior checks |

Discard rows that cannot establish a target link or version support.

## Evidence Order

1. Confirm local manifests, lockfiles, version files, config, and target code path.
2. Inspect installed package metadata, exported types, source, schemas, tests, or bundled docs when available.
3. Consult official documentation for the resolved version or an explicitly compatible version range.
4. Use official release notes or migration guides only when evaluating an upgrade.
5. Use authoritative platform guidance for deployment/runtime behavior.

Record source URL, applicable version, access date when useful, and the claim it supports. Treat community material as a lead, not proof. Never apply latest-version documentation to an older major version without explicit compatibility evidence.

## Dependency Rules

- Prefer capabilities of an existing direct dependency when they fit required semantics and outperform alternatives under the rubric.
- Do not preserve a package merely because it is already installed; include bundle/runtime, security, update, ownership, and conceptual costs.
- Do not import transitive dependencies directly. If chosen, declare the dependency and accept compatibility ownership explicitly.
- Add a dependency only when total custom code, concepts, operational burden, and verification cost decrease enough to justify it.
- Upgrade only for a named capability, fix, compatibility need, or supported-runtime requirement. Isolate the migration from unrelated optimization work when possible.
- Before replacing custom code, enumerate its required semantics: validation, error behavior, ordering, retries, auth, cancellation, observability, lifecycle, compatibility, and extension points.

## Optimization Passes

Run only the pass connected to the target.

### Frontend and Rendering

Inspect routing/rendering mode, server/client boundaries, hydration, data loading, request deduplication, code splitting, tree shaking, asset/image/font handling, state subscriptions, render profiles, virtualization, and bundle transforms. Use memoization or lazy loading only when profiles and interaction semantics support them.

### Backend and API

Inspect middleware order, request lifecycle, serialization, validation duplication, client/connection reuse, pooling, batching, streaming, compression, caching, cancellation, timeouts, retries, concurrency limits, and observability hooks. Preserve auth, error contracts, and backpressure.

### Database and ORM

Inspect generated SQL, query count, selected columns, relationship loading, batching, pagination, transactions, prepared statements, indexes, connection pools, and query plans. Confirm data distribution, write cost, locking, and migration/rollback before indexes or query-shape changes.

### Runtime and Language

Inspect supported compiler/runtime modes, startup, allocation, garbage collection, scheduling, async/concurrency primitives, serialization, native profiling, and standard-library capabilities. Do not tune runtime flags without representative workload evidence and deployment parity.

### Build and Bundling

Inspect incremental compilation, persistent/shared caches, task graphs, content hashing, tree shaking, minification, source maps, transpilation targets, generated code, plugin cost, and duplicate transforms. Verify production output as well as wall time.

### Tests

Inspect discovery, environment startup, global setup, fixtures, database/browser reuse, isolation, workers, sharding, changed-test selection, coverage transforms, retries, and slow-test reports. Preserve determinism, isolation, coverage, and failure diagnostics.

### CI/CD

Inspect critical path, native caching, cache keys, artifacts, job dependencies, concurrency controls, matrix duplication, container setup, deployment previews, retries, and cancellation of superseded work. Optimize time-to-trust, not only total compute time.

### Deployment and Platform

Inspect platform-native build caching, regions, edge/serverless modes, cold starts, connection constraints, image layers, autoscaling, health checks, compression/CDN behavior, observability, and rollback support. Confirm local recommendations match the actual deployment target.

## Compatibility and Operational Gates

Before recommending or implementing an ecosystem capability, answer:

- Is it supported by the resolved version and enabled execution mode?
- Do installed plugins, adapters, runtime versions, and deployment constraints support it?
- Does it preserve required behavior and custom semantics?
- What memory, CPU, storage, network, bundle, security, and maintenance costs does it add?
- Can it be measured on the named workflow and observed in production or CI where relevant?
- Can it be introduced incrementally and reverted without data or contract damage?

Reject or defer the capability if any critical answer is unknown and cannot be confirmed before implementation.
