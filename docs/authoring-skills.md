# Authoring Skills

## Authoring Workflow

1. Create a new skill directory under `skills/<domain>/<skill-name>/`.
2. Add `SKILL.md` with required frontmatter (`name`, `description`).
3. Add bundled scripts, templates, or references under `scripts/`, `templates/`, `references/`.
4. Register the new skill in `catalog/skills.yaml` with appropriate `kind`, `status`, and `invocation`.
5. Add unit and contract tests under `tests/skills/<skill-name>/`.
6. Add human-facing documentation in `docs/skills/<skill-name>.md`.
7. Run `python tools/catalog/sync_catalog.py --write` to update generated surfaces.
8. Validate using `python tools/validation/validate_repository.py`.
