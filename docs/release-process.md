# Release Process & Protocol

This monorepo uses single monorepo Semantic Versioning stored in `VERSION`.

---

## Pre-Release Checklist

Before tagging a release or building distribution assets, execute the following protocol in order:

### 1. Update Version File
Update the single version string in `VERSION`:
```text
1.0.0
```

### 2. Update Changelog
Document all notable additions, changes, and fixes in `CHANGELOG.md` under the new version header following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

### 3. Regenerate Skill Catalog
Run catalog synchronization to update markdown tables in `README.md` and `skills/engineering/README.md`:
```bash
python tools/catalog/sync_catalog.py --write
```

### 4. Run Version & Pre-Flight Checkers
```bash
python tools/release/check_version.py
python tools/catalog/validate_catalog.py
python tools/catalog/sync_catalog.py --check
```

### 5. Run Full Repository Validation
```bash
python tools/validation/validate_repository.py
python tools/validation/validate_links.py
python tools/validation/validate_dependencies.py
```

### 6. Build & Verify Distribution Artifacts
```bash
python tools/packaging/build_distribution.py
python tools/packaging/verify_distribution.py
```
Ensures that distribution archives are built cleanly and contain no forbidden test artifacts or development cache files.

### 7. Run Test & Type Checkers
```bash
ruff check .
python tools/validation/run_mypy.py
python -m pytest -q
```

### 8. Perform Manual Smoke Tests

Verify skill resolution:
- **skills.sh CLI**: `npx skills add akshay-diwadkar/skills` (verify skills resolve)

### 9. Tag Release & Verify Artifacts
Create the git release tag only after all automated verification gates and manual smoke tests pass cleanly:
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
```
*(Note: Do not push tags or update remotes without explicit user authorization.)*
