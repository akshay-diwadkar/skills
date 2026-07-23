# Testing & Verification Strategy

This monorepo employs a multi-layered testing strategy to guarantee repository integrity, schema compliance, cross-platform compatibility, and skill contract enforcement.

---

## 1. Test Layer Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           Automated CI Suite                            │
├──────────────────┬───────────────────┬────────────────┬─────────────────┤
│ Contract & Catalog│ Repository       │ Unit & Script  │ Packaging &     │
│ Validation       │ Boundaries        │ Test Suite     │ Manifest Tests  │
│ (validate_catalog│ (validate_repo-   │ (pytest)       │ (verify_distrib-│
│ & sync_catalog)  │  sitory)          │                │  ution)         │
└──────────────────┴───────────────────┴────────────────┴─────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Optional Local Verification                      │
├──────────────────────────────────────┬──────────────────────────────────┤
│ Browser Smoke Tests (Playwright)     │ Live Model Evaluations           │
│ (tests/create-diagram/browser_smoke) │ (tests/*/run_live_evaluations)   │
└──────────────────────────────────────┴──────────────────────────────────┘
```

---

## 2. Default CI Checks

These commands are run automatically on CI (Python 3.11):

### 1. Catalog Validation & Sync
```bash
python tools/catalog/validate_catalog.py
python tools/catalog/sync_catalog.py --check
```
Verifies YAML schema compliance, link target resolution, and ensures that all generated platform adapters and documentation tables match catalog sources of truth.

### 2. Repository Structure & Boundary Check
```bash
python tools/validation/validate_repository.py
```
Ensures that:
- Canonical skills reside under `skills/engineering/`.
- Runtime skill folders contain zero test files, dev scripts, or caches.
- Skill frontmatter matches folder names.
- Locks and catalog definitions remain in sync.

### 3. Documentation Link & Dependency Check
```bash
python tools/validation/validate_links.py
python tools/validation/validate_dependencies.py
```
Validates relative markdown link targets and checks dependencies.

### 4. Distribution Packaging Verification
```bash
python tools/packaging/verify_distribution.py
```
Builds a distribution package in a temporary directory and verifies that all required runtime files exist while dev artifacts are excluded.

### 5. Static Analysis & Type Checking
```bash
ruff check .
python tools/validation/run_mypy.py
```
*Note*: Mypy is run per skill via `run_mypy.py` to prevent duplicate-module collision errors across independent skill packages.

### 6. Automated Pytest Suite
```bash
python -m pytest -q
```
Runs unit tests for bundled scripts, platform manifest tests, agent generation tests, contract validators, and cross-platform diagram tests.

---

## 3. Optional & Environment-Specific Tests

### Diagram Visual & Browser Smoke Tests
`create-diagram` includes browser smoke tests using Playwright to verify SVG/HTML rendering:

```bash
# Install optional test dependencies
python -m pip install playwright
python -m playwright install chromium

# Run browser smoke test
python tests/create-diagram/browser_smoke.py
```

### Live Model Evaluations
Skills with live evaluation frameworks (`implement-with-senior-dev`, `design-codebase-with-senior-dev`, `optimize-codebase-with-senior-dev`) use provider-neutral evaluation runners. See [Live Evaluations](evaluations.md) for execution details.
