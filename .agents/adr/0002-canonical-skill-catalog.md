# ADR 0002: Canonical Skill Catalog

## Status

Accepted

## Context

Skill metadata (name, domain, status, kind, invocation mode, platform compatibility, relationships) was previously scattered across individual `SKILL.md` frontmatter, markdown READMEs, lockfiles, and CI configuration. This led to drift and manual sync overhead.

## Decision

We establish `catalog/skills.yaml` backed by `catalog/skills.schema.json` as the single authoritative, machine-readable source of truth for repository skill governance.

`tools/catalog/sync_catalog.py` deterministically generates or validates:
- The catalog table in root `README.md` (`<!-- BEGIN GENERATED SKILL CATALOG -->`).
- `skills/engineering/README.md`.
- Platform manifests (`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`).

## Consequences

- Zero duplication of manually edited skill metadata.
- Automated CI drift detection (`sync_catalog.py --check`).
- Strict schema validation for catalog entries.
