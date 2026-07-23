# Design Codebase With Senior Dev

Assess whether architectural change is justified and choose the smallest evidence-backed design, with an incremental behavior-preserving migration path.

## When to Use

- When evaluating major subsystem restructuring, boundary shifts, or state-ownership changes.
- When assessing whether an architectural refactor is justified before modifying code.

## When NOT to Use

- For implementing changes directly (this skill is assessment-only).

## Key Inputs & Outputs

- **Input**: Problem statement, target codebase files.
- **Output**: Validated Codebase Design Assessment artifact.

## Bundled Validators & Tools

- `check_assessment.py`: Validates assessment structure and trade-off justification.

## Workflow Integration

Handoffs approved assessments to `plan-with-senior-dev`.
