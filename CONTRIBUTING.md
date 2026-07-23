# Contributing Guide

Contributions to this engineering skills repository are welcome.

## Development & Submission Process

1. Register new skills or metadata updates in `catalog/skills.yaml`.
2. Follow the domain structure (`skills/engineering/<skill-name>/`).
3. Place tests in `tests/skills/<skill-name>/`.
4. Run `python tools/catalog/sync_catalog.py --write` to update generated catalog tables and manifests.
5. Verify all checks pass before submitting a pull request:

```bash
python tools/catalog/validate_catalog.py
python tools/catalog/sync_catalog.py --check
python tools/validation/validate_repository.py
python tools/packaging/verify_distribution.py
ruff check .
mypy .
python -m pytest -q
```
