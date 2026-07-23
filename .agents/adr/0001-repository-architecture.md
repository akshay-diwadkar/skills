# ADR 0001: Repository Architecture

## Status

Accepted

## Context

The previous repository layout stored active skills as flat, un-namespaced folders at the root directory alongside tests, scripts, and configuration. As the number of skills grew, this created collisions, path confusion, unscalable distribution boundaries, and difficulty classifying skills by domain.

## Decision

We restructure the repository into a domain-organized canonical skill structure:

- All active engineering skills reside under `skills/engineering/<skill-name>/`.
- `create-diagram` is categorized in the `engineering` domain alongside software planning and architecture skills.
- Skill development test suites move to `tests/skills/<skill-name>/`.
- Repository governance metadata resides in `catalog/skills.yaml`.

## Consequences

- Stable, deterministic canonical skill paths (`skills/engineering/<skill-name>`).
- Clean packaging boundaries separating runtime skill packages from development tests.
- Simplified `.gitignore` rules based on explicit directory trees.
