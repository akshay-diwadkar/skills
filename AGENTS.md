# Agent Guidelines & Repository Architecture

This repository is a production-grade engineering skill monorepo.

## Rules & Constraints

1. **Canonical Locations**: All skills live under `skills/engineering/<skill-name>/`. Do not create skills outside `skills/<domain>/`.
2. **Catalog Ownership**: `catalog/skills.yaml` and `catalog/agents.yaml` are the single machine-readable sources of truth for skill and agent metadata. Run `python tools/catalog/sync_catalog.py --write` whenever catalog metadata changes.
3. **Agent Source Prompts**: Canonical agent prompts live under `agents/source/`. Platform adapters (`agents/claude/`, `agents/cursor/`, `.codex/agents/`) are generated automatically by `sync_catalog.py`. Do not edit generated adapters directly.
4. **Packaging Boundaries**: Skill folders under `skills/` contain ONLY runtime-required files. Development tests, evals, and fixtures MUST reside under `tests/`.
5. **Lifecycle as Metadata**: Do not create maturity folders (`experimental/`, `stable/`). Store maturity state in catalog YAML files.
6. **Validation Gates**: Always run `python tools/validation/validate_repository.py` and `python tools/catalog/sync_catalog.py --check` before finalizing changes.
7. **No Remote Write**: Do not commit, push, create releases, or modify Git remotes without explicit user request.
