# Repository Architecture

## Structure Overview

This repository is structured as a production-grade engineering skill monorepo:

- `skills/`: Canonical, domain-organized skill directories (`skills/engineering/<skill-name>/`).
- `catalog/`: Authoritative repository metadata (`skills.yaml` and `skills.schema.json`).
- `docs/`: Human-facing documentation, architectural decision records, and skill guides.
- `tools/`: Build, validation, synchronization, packaging, and release tooling.
- `tests/`: Organized test suites separated from distributable skill packages.
- `.claude-plugin/`: Distribution manifests for Claude Plugin platform.

## Design Principles

1. **Stable Canonical Paths**: Skill maturity (lifecycle) is metadata stored in `catalog/skills.yaml`, not encoded in directory paths.
2. **Single Source of Truth**: The central catalog (`catalog/skills.yaml`) drives all generated READMEs, manifests, and indexes.
3. **Clean Packaging Boundaries**: Distributable skills contain only runtime-required files (instructions, scripts, templates, references). Tests and evals reside strictly in `tests/`.
4. **Enforced Verification**: Automated verification gates ensure schema compliance, link integrity, packaging correctness, and test suite execution.
