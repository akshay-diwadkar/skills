# Agent Guidelines & Repository Architecture

This repository is a production-grade engineering skill monorepo.

## Rules & Constraints

1. **Canonical Locations**: All skills live under `skills/engineering/<skill-name>/`. Do not create skills outside `skills/<domain>/`.
2. **Catalog Ownership**: `catalog/skills.yaml` is the single machine-readable source of truth for skill metadata. Run `python tools/catalog/sync_catalog.py --write` whenever catalog metadata changes.
3. **Packaging Boundaries**: Skill folders under `skills/` contain ONLY runtime-required files. Development tests, evals, and fixtures MUST reside under `tests/skills/<skill-name>/`.
4. **Lifecycle as Metadata**: Do not create maturity folders (`experimental/`, `stable/`). Store maturity state in `catalog/skills.yaml`.
5. **Validation Gates**: Always run `python tools/validation/validate_repository.py` and `python tools/catalog/sync_catalog.py --check` before finalizing changes.
6. **No Remote Write**: Do not commit, push, create releases, or modify Git remotes without explicit user request.
