# Implement With Senior Dev

Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report.

## When to Use

- When an approved implementation plan exists (e.g., produced by `plan-with-senior-dev`).
- When implementing a feature or fix incrementally with mandatory verification steps.

## When NOT to Use

- When requirement details or design contracts are still vague or unvalidated (use `plan-with-senior-dev`).

## Key Inputs & Outputs

- **Input**: Approved `plan.md` artifact.
- **Output**: Verified implementation code patch and change report.

## Bundled Validators & Tools

- `check_implementation.py`: Verifies plan alignment and change compliance.
- `finalize_implementation.py`: Computes change receipts and finalizes report.

## Workflow Integration

Receives input from `plan-with-senior-dev` and `github-issue-planner`.
