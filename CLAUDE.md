# Claude Maintainer Guide

Companion maintenance rules for Claude Code and subagents.

## Core Commands

- **Validate Catalog**: `python tools/catalog/validate_catalog.py`
- **Sync Catalog**: `python tools/catalog/sync_catalog.py --write` (or `--check`)
- **Validate Repository**: `python tools/validation/validate_repository.py`
- **Build Distribution**: `python tools/packaging/build_distribution.py`
- **Verify Distribution**: `python tools/packaging/verify_distribution.py`
- **Run Tests**: `python -m pytest -q`
- **Run Linter**: `ruff check .`
- **Run Type Checker**: `python tools/validation/run_mypy.py`

## Key Boundaries

- Distributable skills: `skills/engineering/<skill-name>/`
- Test suites: `tests/skills/<skill-name>/` and `tests/repository/`
- Authoritative metadata: `catalog/skills.yaml`
