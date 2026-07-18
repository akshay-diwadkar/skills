# Evidence-Gated Documentation Research

Use this protocol only after a `B-n` or bounded static leverage point identifies a component that can affect the named workflow. Documentation validates a candidate; it does not create the target.

## Resolve Before Search

Confirm exact installed version from lockfiles or installed metadata, then manifests, runtime files, containers, CI, and deployment configuration. Record actual imports, commands, configuration, plugins, execution mode, and direct/transitive ownership. Lower confidence when the resolved minor version is unavailable; reject claims based on a different major version.

## Research Targets

Research a component only when local evidence shows that it:

- participates in the measured or statically evidenced path;
- controls a relevant performance, cost, reliability, or feedback-loop mechanism;
- may replace locally observed custom machinery; or
- defines a compatibility constraint for a concrete candidate.

Do not inventory every available option, search every installed package, or treat an unset setting as a finding.

## Source Order

1. Local config, types, schemas, package metadata, source, tests, and bundled docs.
2. Official documentation matching the resolved version or supported range.
3. Official tuning/production guides.
4. Official release notes or migration guides only for a named upgrade candidate.
5. Authoritative platform guidance for the actual deployment model.

Community sources may locate primary material but never support a promoted claim.

## Cross-Reference

For each plausible capability, record one `R-n` with component, resolved version, specific official URL, finding, target `B-n`, current local state, compatibility, expected mechanism, and verification. Check repository comments, ADRs, tests, and history for intentional divergence.

Promote only when:

- the capability addresses the evidenced leverage point;
- the installed version and execution mode support it;
- required custom semantics are preserved;
- operational and security costs are acceptable; and
- the named workflow can verify the result.

If no ecosystem claim is required, record one explicit not-applicable `R-n`. If version or compatibility remains unresolved, set the candidate compatibility gate to `no` and classify it `investigate` with a safe experiment.

## Domain Lookup Lenses

Use only lenses connected to the target:

- **Runtime/backend:** pooling, batching, serialization, streaming, timeouts, retries, concurrency, lifecycle, graceful shutdown.
- **Frontend/build:** render boundaries, code splitting, assets, tree shaking, incremental compilation, caches, source maps, deployment output.
- **Database/data:** query plans, selected columns, relationship loading, indexes, batching, transactions, connection pools, partitioning, pushdown.
- **Tests/CI:** startup, fixtures, workers, sharding, affected-test selection, coverage overhead, caching, artifacts, job critical path, superseded-run cancellation.
- **Deployment/platform:** cold starts, resource limits, regions, autoscaling, health checks, CDN/compression, rollback and observability.
- **ML/data engineering:** loaders, batch size, precision, hardware modes, distributed execution, checkpointing, formats, partitioning, schema evolution.

The lens is a search aid, not a recommendation checklist. Omit claims with no local delta, concrete benefit, or verification path.
