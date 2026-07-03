# Ecosystem Optimization

Use this reference only after the local repo inventory identifies a concrete framework, package, runtime, build tool, test tool, deployment target, or CI/tooling setup that may be misused. Web research supplements local evidence; it never creates a finding by itself.

## Inventory

Record the local ecosystem before searching the web:

- runtime and language versions;
- application frameworks and major libraries;
- package manager and lockfile;
- build, bundling, linting, formatting, and type-checking tools;
- test runner, coverage, browser, emulator, fixture, or integration-test tools;
- deployment, hosting, container, database, queue, cache, observability, and CI/CD tools;
- versions and config files when available.

Use manifests, lockfiles, framework configs, build/test configs, CI files, Dockerfiles, deployment config, and version files as inventory evidence.

## Web Research

Search only after the inventory identifies the relevant ecosystem. Prioritize current primary or authoritative sources:

- official framework, package, runtime, and tool documentation;
- release notes, changelogs, migration guides, and deprecation notices;
- security advisories and vulnerability databases;
- package registry metadata;
- vendor performance, deployment, caching, and build guidance.

Use community posts only as leads unless the claim is independently supported by local evidence or primary documentation.

## Compare Capabilities

Compare local usage against documented capabilities and defaults:

- caching, incremental builds, build cache sharing, and CI cache keys;
- compiler, transpiler, minifier, bundler, tree-shaking, and source-map settings;
- framework modes, routing/data-loading primitives, rendering modes, hydration, prefetching, and asset optimization;
- package versions, deprecated APIs, migration opportunities, and security fixes;
- test runner parallelism, sharding, browser reuse, coverage scope, fixture cost, and integration boundaries;
- deployment/runtime flags, container layering, serverless/edge settings, database or queue client options, and observability hooks;
- known performance primitives for rendering, querying, scheduling, caching, batching, pooling, and concurrency.

## Drafting Rules

Draft an optimization issue only when all are true:

- local evidence shows the repo uses or configures the ecosystem component in a suboptimal, outdated, or risky way;
- primary-source web evidence shows a relevant capability, safer default, migration path, or optimization;
- the expected benefit is concrete: faster build/test/runtime path, lower operational risk, stronger security posture, simpler maintenance, or clearer architecture;
- the fix is independently actionable and can be verified.

Reject speculative suggestions. Do not draft "upgrade because newer exists" issues unless the newer capability materially applies to the repo and the local code can use it. Do not create broad modernization epics; draft one issue per missed capability, misconfiguration, or outdated behavior.

## Evidence Format

Include both evidence types in the issue:

- local evidence: file paths, command output, dependency metadata, or config excerpts;
- external evidence: links to official docs, release notes, advisories, registry metadata, or vendor guides;
- expected benefit and acceptance criteria.
