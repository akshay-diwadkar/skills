# Release Process

## Versioning Model

This repository uses single monorepo Semantic Versioning stored in `VERSION`.

## Pre-Release Check Protocol

Before tagging a release, run:

```bash
python tools/release/check_version.py
python tools/catalog/sync_catalog.py --check
python tools/validation/validate_repository.py
python tools/packaging/build_distribution.py
python tools/packaging/verify_distribution.py
python -m pytest -q
```

Publication occurs only upon explicit release authorization.
