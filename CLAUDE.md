# Claude Maintainer Guide

Companion maintenance rules for Claude Code and subagents.

## Core Commands

- **Validate Catalog**: `python tools/catalog/validate_catalog.py`
- **Sync Catalog**: `python tools/catalog/sync_catalog.py --write` (or `--check`)
- **Install Codex Agents**: `python tools/agents/install_codex_agents.py --target /path/to/project --write`
- **Validate Repository**: `python tools/validation/validate_repository.py`
- **Build Distribution**: `python tools/packaging/build_distribution.py`
- **Verify Distribution**: `python tools/packaging/verify_distribution.py`
- **Run Tests**: `python -m pytest -q`
- **Run Linter**: `ruff check .`
- **Run Type Checker**: `mypy .`

## Key Boundaries

- Distributable skills: `skills/engineering/<skill-name>/`
- Agent source prompts: `agents/source/`
- Generated adapters: `agents/claude/`, `agents/cursor/`, `.codex/agents/`
- Test suites: `tests/skills/<skill-name>/` and `tests/repository/`
- Authoritative metadata: `catalog/skills.yaml` and `catalog/agents.yaml`
