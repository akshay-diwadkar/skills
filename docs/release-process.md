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

### 3. Regenerate Catalogs & Platform Adapters
Run catalog synchronization to update generated platform manifests (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`), TOML agents (`.codex/agents/`), adapter prompts, and documentation markdown tables:
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

### 8. Tag Release & Verify Artifacts
Create the git release tag only after all automated verification gates pass cleanly:
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
```
*(Note: Do not push tags or update remotes without explicit user authorization.)*
