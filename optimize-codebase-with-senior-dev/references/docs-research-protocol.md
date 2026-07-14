# Documentation Research Protocol

Use this protocol to systematically research official documentation for every significant component in the target repo. The goal is to surface optimization capabilities the repo is not currently exploiting. Local evidence defines the target; documentation research quantifies the gap between current use and available capability.

## Contents

- Research trigger criteria
- Version resolution
- Research execution
- Cross-reference protocol
- Domain-specific research playbooks
- Evidence quality standards
- Documentation research log format

## Research Trigger Criteria

Research a component's documentation when any of the following hold:

- It is a core framework: web framework, ML framework, data processing framework, ORM, query builder, state manager, or rendering engine.
- It handles a performance-sensitive workflow: training, inference, data pipelines, API serving, build, bundling, test execution, or deployment.
- It has configurable behavior that affects performance, cost, resource usage, or output quality.
- The repo uses it in a non-trivial way: multiple imports, dedicated configuration, custom wrappers, or central to a traced workflow.
- It is infrastructure: Spark, Kubernetes, Docker, cloud services, CI/CD platforms, databases, caches, queues, or CDNs.

Do **not** deep-research simple utility libraries (lodash, pathlib, itertools), formatting tools (prettier, black), or trivial dev dependencies unless the target workflow traces through them.

## Version Resolution

Before reading any documentation, resolve the installed version:

1. Check lockfiles first: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Pipfile.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`.
2. Fall back to manifests: `package.json`, `pyproject.toml`, `setup.cfg`, `requirements.txt`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `build.gradle`, `pom.xml`.
3. Check runtime version files: `.node-version`, `.python-version`, `.ruby-version`, `.tool-versions`, `runtime.txt`, `.nvmrc`.
4. Check container and CI definitions for pinned versions: `Dockerfile`, `docker-compose.yml`, `.github/workflows/*.yml`, `.gitlab-ci.yml`.
5. When the lockfile disagrees with the manifest range, trust the lockfile — it reflects the actual installed version.

Record the resolved version as `major.minor.patch` when available. Flag components where the version cannot be resolved and lower confidence on any findings for them.

## Research Execution

For each component that passes the trigger criteria:

### Identify Search Targets

Construct search queries from the component name and resolved version:

- `{library} {version} performance tuning guide`
- `{library} {version} configuration reference`
- `{library} best practices production`
- `{library} optimization tips`
- `{framework} {version} what's new` (to identify capabilities available at the installed version)
- `{library} {version} migration guide` (when the repo may be underusing post-upgrade features)
- `{library} production deployment recommendations`

### Read Official Documentation

Use web search to locate official docs, then read them via URL. Focus reading on:

- **Configuration options** not currently set in the repo: defaults that should be tuned for production, options that enable hardware acceleration, parallelism, caching, or compression.
- **Performance tuning sections**: dedicated guides, benchmarks, recommended settings for production workloads.
- **Best practices and anti-pattern warnings**: patterns the docs explicitly discourage that the repo may be using.
- **Advanced features that could replace custom code**: built-in utilities, middleware, hooks, plugins, or modes that overlap with repo-maintained code.
- **Deployment and production recommendations**: environment variables, runtime flags, server configurations, scaling guidance.
- **What's new and changelog entries**: features added in or before the installed version that the repo has not adopted.

### Record Findings

For every actionable finding, populate a documentation research log entry (format below). Do not record generic advice that cannot be tied to a specific repo behavior or configuration gap.

## Cross-Reference Protocol

After researching a component's docs, systematically compare:

### Configuration Delta

List every configuration option the docs describe as performance-relevant. For each, check whether the repo sets it. Record unset options with their documented default and the docs' recommended production value.

### Custom Code Overlap

Identify repo-maintained code that reimplements behavior the library provides natively. Check wrappers, utilities, middleware, data transformers, validators, retry logic, connection managers, caching layers, and scheduling helpers. For each overlap, record the native API, its version availability, and any semantic gap (error handling, ordering, auth, observability) that may justify the custom implementation.

### Deployment Model Match

Compare the repo's deployment model (serverless, container, edge, monolith, microservice) against the docs' recommendations for that model. Look for mode switches, adapter selections, resource limits, connection pool sizes, timeout values, and scaling configurations that differ from the docs' guidance.

### Default vs Recommended

Identify parameters left at library defaults that the docs recommend tuning for production workloads. Common categories: worker/thread counts, pool sizes, buffer sizes, timeout values, retry policies, batch sizes, cache TTLs, log levels, serialization formats, and compression settings.

The delta between what the repo configures and what the docs recommend IS the optimization surface. No delta means no finding — move on.

## Domain-Specific Research Playbooks

Research the following areas when the target repo operates in the corresponding domain. Each item is a documentation lookup target, not a recommendation.

### ML / AI

**Training**: batch size guidance, learning rate schedule APIs, mixed precision support and flags, distributed training modes, data loader worker count and prefetch settings, preprocessing pipeline parallelism, gradient accumulation, model checkpoint format and frequency, memory optimization (gradient checkpointing, activation offloading).

**Inference**: model optimization APIs (quantization, pruning, graph optimization, ONNX/TensorRT export), batch inference configuration, prediction caching, hardware acceleration flags (CUDA, MPS, XLA), model warm-up, dynamic batching, serving framework integration.

**AutoML / Experiment frameworks**: search space configuration, time and resource budget settings, presets and quality levels, ensemble methods, feature engineering toggles, early stopping configuration, trial parallelism.

**Data**: format recommendations (Parquet vs CSV vs Feather vs Arrow), partitioning strategies, lazy vs eager loading modes, schema enforcement, column pruning, predicate pushdown, memory-mapped I/O.

### Data Engineering

**Spark / PySpark**: partition count tuning, shuffle partition settings, broadcast join thresholds, Catalyst optimizer hints, serialization (Kryo vs Java), memory fraction tuning, adaptive query execution, dynamic resource allocation, columnar batch processing, data skew handling.

**Database**: query plan analysis tools, index recommendations, connection pool sizing, prepared statement reuse, batch insert/upsert APIs, read replica routing, query timeout configuration, explain/analyze integration, materialized views, partition pruning.

**ETL / Pipelines**: incremental processing modes, checkpointing and recovery, schema evolution handling, backfill strategies, idempotent write patterns, dead-letter queues, watermark and late-data configuration.

### Web / API

**Framework**: middleware ordering and short-circuit behavior, response compression, static file serving optimization, keep-alive and connection reuse, request validation libraries with compile-time schema, async handler support, streaming responses, graceful shutdown.

**Frontend**: code splitting configuration, tree shaking settings, lazy loading routes and components, image optimization (formats, sizing, lazy load), caching headers and strategies, service worker configuration, SSR/SSG/ISR mode selection, font loading strategy, CSS extraction and purging.

**Caching**: cache strategy selection (stale-while-revalidate, cache-aside, write-through), TTL tuning guidance, cache key design, distributed cache configuration, cache warming, eviction policies, serialization format for cached values.

### Infrastructure

**Container**: multi-stage build patterns, layer ordering for cache efficiency, image size optimization (distroless, Alpine, slim), resource limit and request settings, health check configuration, signal handling.

**CI/CD**: job parallelism, dependency caching (keys, paths, restore strategy), artifact upload and reuse, incremental build modes, test sharding and splitting, matrix deduplication, concurrency groups, timeout configuration, cancellation of superseded runs.

**Cloud / Platform**: instance type and sizing guidance, autoscaling policies and metrics, spot/preemptible instance configuration, region selection for latency, CDN and edge caching, managed service scaling knobs, cold start mitigation.

**Monitoring / Observability**: sampling rate configuration, log level management, metric cardinality limits, trace context propagation, structured logging format, alert threshold guidance.

### Build & Test

**Compiler / Bundler**: incremental compilation modes, persistent cache configuration, tree shaking depth, source map strategy (hidden, nosources, inline), transpilation target selection, chunk splitting strategy, minification options, dead code elimination.

**Test runner**: parallel execution settings, worker count and isolation, test selection by change, fixture sharing and lifecycle, coverage collection overhead, snapshot update strategy, timeout per test, retry configuration for flaky tests.

## Evidence Quality Standards

### Required

- Cite documentation that matches the installed major version. Same minor version is preferred; same major is required.
- Record the specific documentation URL for every finding.
- When a doc recommendation contradicts current repo behavior, check repo comments, ADRs, commit messages, and git history for an intentional reason before recording it as a gap.

### Confidence Adjustments

- **High confidence**: doc matches resolved major.minor version; finding is in a dedicated tuning or production guide; repo has no documented reason for the current approach.
- **Medium confidence**: doc matches major version but not minor; finding is in general docs rather than a tuning guide; or repo has partial configuration suggesting awareness of the area.
- **Low confidence**: doc is for a different minor version with uncertain compatibility; finding is inferred from changelog or release notes rather than a tuning guide; or the repo may have an undocumented reason for its approach.

### Disqualified Sources

Never cite blog posts, StackOverflow answers, community guides, Medium articles, or tutorial sites as primary evidence. Use them only as leads to locate official documentation. If no official doc supports the finding, record it as unverified and lower confidence to low.

## Documentation Research Log

For each researched component, produce one entry per actionable finding:

```
Component: {name}
Version: {resolved version from lockfile or manifest}
Source: {official documentation URL}
Access Date: {date the doc was read}
Finding: {specific capability, parameter, configuration option, or pattern}
Current State: {how the repo handles this — config value, custom code, or absent}
Recommended State: {what the docs suggest for production workloads}
Expected Benefit: {performance, cost, quality, reliability, or maintainability improvement}
Confidence: {high | medium | low}
Confidence Rationale: {version match quality, doc specificity, repo context}
Compatibility: {version constraints, runtime requirements, deployment prerequisites, breaking changes}
Verification: {how to measure the effect — command, metric, before/after comparison}
```

### Log Rules

- One entry per finding. Do not combine multiple unrelated findings into a single entry.
- Omit entries where the repo already follows the documented recommendation.
- Omit entries where the expected benefit cannot be articulated concretely.
- Include entries where the repo explicitly diverges from documentation recommendations, even when the divergence may be intentional — flag these for review rather than silent adoption.
- Link findings to the capability matrix in `ecosystem-leverage.md` when they identify a native capability the repo underuses.
- Feed high-confidence, high-impact findings into the candidate ledger in `optimization-protocol.md` for ranking and implementation planning.

## Sequencing With Other References

1. Build the ecosystem inventory per `ecosystem-leverage.md` to identify which components to research.
2. Execute this documentation research protocol for each inventoried component that passes the trigger criteria.
3. Record findings in the documentation research log.
4. Cross-reference findings against the repo's current configuration and code.
5. Promote actionable findings to the capability matrix in `ecosystem-leverage.md`.
6. Score promoted findings using `optimization-rubric.md`.
7. Plan and execute approved candidates per `optimization-protocol.md`.

Do not skip ecosystem inventory and jump directly to documentation research. The inventory defines the research scope; undirected documentation reading wastes effort and produces findings disconnected from the target workflow.
