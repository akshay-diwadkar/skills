# Engineering Skills

[![Repository Quality](https://github.com/akshay-diwadkar/skills/actions/workflows/quality.yml/badge.svg?branch=main&event=push)](https://github.com/akshay-diwadkar/skills/actions/workflows/quality.yml?query=branch%3Amain)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

Reusable engineering skills for coding agents and human engineers. Each skill is self-contained under `skills/engineering/`; tests and repository validation live alongside the source.

## Skills

- `build-codebase-knowledge`
- `codebase-issue-auditor`
- `create-diagram`
- `design-codebase-with-senior-dev`
- `github-issue-planner`
- `implement-with-senior-dev`
- `optimize-codebase-with-senior-dev`
- `plan-with-senior-dev`

## Use locally

Copy or symlink the skill directory you need into your agent's skills directory. Read its `SKILL.md` and use only its bundled task resources.

## Verification

```bash
ruff check .
python tools/validation/run_mypy.py
python tools/validation/validate_repository.py
python -m pytest -q
```
