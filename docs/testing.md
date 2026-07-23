# Testing Strategy

## Test Organization

- `tests/skills/<skill-name>/`: Skill-specific test suites.
  - `unit/`: Unit tests for bundled python scripts.
  - `contract/`: Contract and rubric enforcement tests.
  - `evals/`: Model capability and live evaluation fixtures.
  - `fixtures/`: Test data fixtures.
- `tests/repository/`: Monorepo contract and catalog synchronization tests.
- `tests/integration/`: Packaging and distribution smoke tests.

## Running Tests

```bash
# Run full pytest suite
python -m pytest -q

# Run repository validation
python tools/validation/validate_repository.py
```
