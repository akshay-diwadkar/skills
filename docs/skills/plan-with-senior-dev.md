# Plan With Senior Dev

Turn features, bug fixes, refactors, migrations, public contracts, or risky integrations into repository-grounded, decision-complete implementation blueprints.

## When to Use

- When planning a code change before writing implementation code.
- When an issue touches public contracts, data migrations, security, concurrency, or multi-subsystem boundaries.
- When requiring contract-v3 validation and receipt stamping.

## When NOT to Use

- For trivial one-line fixes where no design decisions or risk tradeoffs exist.
- When executing an already approved plan (use `implement-with-senior-dev`).

## Key Inputs & Outputs

- **Input**: Problem description, target code files, and user intent.
- **Output**: Formatted implementation blueprint (`plan.md`) with explicit fact anchors, change records, risk coverage, and validation receipt.

## Bundled Validators & Tools

- `check_plan.py`: Validates plan semantics, required sections, fact citations, and blueprint completeness.
- `finalize_plan.py`: Stings receipt onto approved plan.

## Workflow Integration

Complements `implement-with-senior-dev` and `design-codebase-with-senior-dev`.
