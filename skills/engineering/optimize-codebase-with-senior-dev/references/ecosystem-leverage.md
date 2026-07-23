# Ecosystem Leverage

Use this reference after a baseline or bounded static leverage point names a relevant framework, package, runtime, database, build/test tool, CI system, or deployment platform. Local evidence selects what to research; ecosystem research does not create an optimization target.

## Contents

- Ecosystem inventory
- Capability matrix
- Evidence order
- Dependency rules
- Optimization passes
- Cross-component optimization
- Compatibility and operational gates

## Ecosystem Inventory

Inventory only components that participate in the evidenced target path:

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

## Cross-Component Optimization

Optimizations at component boundaries often yield higher ROI than optimizing individual components in isolation. After completing the single-component inventory, analyze interaction patterns.

### Interaction Inventory

For each pair of components on the target path, record:

| Field | Content |
| --- | --- |
| Components | The two interacting components and their roles |
| Boundary type | Data handoff, API call, file I/O, serialization, shared state, event, queue, or network |
| Current pattern | How data or control flows between them now |
| Serialization format | What format crosses the boundary (JSON, Pickle, Parquet, Protobuf, Arrow, CSV, custom) |
| Volume and frequency | Data size, request rate, or batch size at the boundary |
| Bottleneck evidence | Profiling, timing, or code-path evidence of friction at this boundary |

### Common Cross-Component Optimization Patterns

- **Serialization format mismatch**: Components that serialize to one format and immediately deserialize in another. Look for opportunities to use a shared in-memory or columnar format (e.g., Arrow between Pandas and Spark, Parquet between training and inference).
- **Redundant data transformation**: Data transformed into an intermediate representation that could be skipped. Look for chains like read CSV → parse → convert DataFrame → serialize → deserialize → convert again.
- **Connection and client reuse**: Components that create new connections or client instances per request when persistent connections, connection pools, or shared clients are supported.
- **Batch size mismatch**: A producer generating records one at a time while the consumer supports batch ingestion, or vice versa.
- **Duplicate computation**: Two components independently computing the same derived value when one could pass it to the other.
- **Schema enforcement at wrong boundary**: Validation happening at every hop instead of once at ingestion.
- **Orchestration overhead**: An orchestrator polling or synchronously waiting when event-driven or async handoff is supported.
- **Infrastructure co-location**: Components that exchange large data volumes running in different regions, zones, or processes when co-location is supported.

### ML + Data Engineering Boundaries

When ML frameworks interact with data engineering infrastructure:

- Check if the training framework supports reading directly from the data platform's native format (e.g., AutoGluon reading Parquet from S3 instead of loading via Pandas from a database).
- Check if distributed training can leverage the data platform's parallelism (e.g., Spark distributing AutoGluon training across workers).
- Check if model artifacts can be stored in a format that eliminates conversion at inference time.
- Check if feature engineering can be pushed down to the data platform instead of running in Python.
- Check if the inference pipeline can batch requests to amortize model loading cost.

### Web + Database Boundaries

When web frameworks interact with databases or caches:

- Check if the ORM supports batching, prefetching, or dataloader patterns to eliminate N+1 queries.
- Check if the framework supports response streaming to avoid buffering large database results.
- Check if the cache layer can serve stale data while revalidating to reduce tail latency.
- Check if database connection pooling is configured to match the web server's concurrency model.

### Build + Test + CI Boundaries

When build, test, and CI systems interact:

- Check if build artifacts can be shared between CI jobs instead of rebuilding.
- Check if test runner supports running only tests affected by changed files.
- Check if the CI platform's native caching can replace custom cache scripts.
- Check if the build output format is optimal for the deployment target.

## Compatibility and Operational Gates

Before recommending or implementing an ecosystem capability, answer:

- Is it supported by the resolved version and enabled execution mode?
- Do installed plugins, adapters, runtime versions, and deployment constraints support it?
- Does it preserve required behavior and custom semantics?
- What memory, CPU, storage, network, bundle, security, and maintenance costs does it add?
- Can it be measured on the named workflow and observed in production or CI where relevant?
- Can it be introduced incrementally and reverted without data or contract damage?

Reject or defer the capability if any critical answer is unknown and cannot be confirmed before implementation.
