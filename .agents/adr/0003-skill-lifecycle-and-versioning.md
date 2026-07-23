# ADR 0003: Skill Lifecycle and Versioning

## Status

Accepted

## Context

Moving skills between lifecycle directories (e.g. `experimental/`, `stable/`, `deprecated/`) creates breaking path changes for downstream consumers whenever maturity changes.

## Decision

1. **Path Stability**: Skill lifecycle status (`experimental`, `beta`, `stable`, `deprecated`) is stored as metadata in `catalog/skills.yaml`. A skill retains its canonical path (`skills/engineering/<skill-name>`) throughout its lifecycle.
2. **Versioning Strategy**: The repository uses a single monorepo Semantic Version stored in `VERSION`.
3. **Deprecation Policy**: Deprecated skills declare a deprecation reason and replacement in the catalog, remaining in the canonical tree until intentionally removed in a major version release.

## Consequences

- No breaking path modifications when skill maturity changes.
- Clear breaking change expectations documented for maintainers.
