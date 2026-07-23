# Codebase Issue Auditor

Audit a repository for bugs, security and performance risks, test gaps, and architectural or maintainability friction, and draft GitHub issues from confirmed findings.

## When to Use

- When conducting broad repository quality, security, or maintainability audits.
- When hunting for unknown risks or verifying whether prior audit findings were resolved.

## When NOT to Use

- For targeting a single known performance bottleneck (use `optimize-codebase-with-senior-dev`).

## Key Inputs & Outputs

- **Input**: Target repository path, optional audit scope or exclusions.
- **Output**: Verified audit bundle and drafted GitHub issue specifications.

## Bundled Validators & Tools

- `publish_github_issues.py`: Publishes confirmed audit findings to GitHub with user authorization.

## Workflow Integration

Feeds findings into `github-issue-planner` for issue-driven planning.
