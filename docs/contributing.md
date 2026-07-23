# Contributor Guide

Thank you for contributing to the **Engineering Skills** monorepo. This document outlines development standards, repository boundaries, and the validation workflow required for contributions.

---

## 1. Development Principles

1. **Plugin-First & Agent-Grounded**: All skills must be modular, reusable, and registered in the catalog so they can be bundled into platform agents.
2. **Canonical Skill Locations**: Canonical skills reside under `skills/engineering/<skill-name>/`. Do not create skills outside `skills/<domain>/`.
3. **Single Source of Truth**: `catalog/skills.yaml` and `catalog/agents.yaml` drive all generated platform adapters, manifests, and documentation tables. Never edit generated files directly.
4. **Clean Runtime Boundaries**: Distributable skill packages under `skills/` must contain *only* runtime-required files (`SKILL.md`, `scripts/`, `templates/`, `references/`). Tests, benchmarks, and evaluation fixtures belong in `tests/`.

---

## 2. Authoring & Contribution Steps

1. **Register Metadata**: Add new skills to `catalog/skills.yaml` or new agents to `catalog/agents.yaml`.
2. **Implement Skill Package**: Create `skills/engineering/<skill-name>/SKILL.md` with required frontmatter (`name`, `description`).
3. **Add Tests**: Place unit and contract test suites under `tests/skills/<skill-name>/`.
4. **Add Documentation**: Create human-facing documentation under `docs/skills/<skill-name>.md` or `docs/agents/<agent-name>.md`.
5. **Synchronize Catalog Surfaces**:
   ```bash
   python tools/catalog/sync_catalog.py --write
   ```
6. **Run Full Validation Gate**:
   ```bash
   python tools/catalog/validate_catalog.py
   python tools/catalog/sync_catalog.py --check
   python tools/validation/validate_repository.py
   python tools/validation/validate_links.py
   python tools/validation/validate_dependencies.py
   python tools/packaging/verify_distribution.py
   ruff check .
   python tools/validation/run_mypy.py
   python -m pytest -q
   ```

---

## 3. Pull Request Requirements

Before opening a pull request:
- Ensure all validation tools pass with zero errors.
- Do not commit local `.env` files or temporary scratch artifacts.
- Keep commits clean and focused.
- Do not modify Git remotes, release tags, or `VERSION` unless authorized.
