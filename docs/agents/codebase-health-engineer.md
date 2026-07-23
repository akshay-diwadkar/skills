# Codebase Health Engineer Agent

Audit overall repository health, discover confirmed defects, risks, test gaps, and structural pressure, and target measurable optimizations.

## When to Use

- Broad repository quality, security, risk, or test-coverage audits.
- Evaluating structural friction or measuring performance/tooling bottlenecks.

## When NOT to Use

- For executing code fixes directly (this agent is analysis-only by default).

## Included Skills

- `codebase-issue-auditor`
- `design-codebase-with-senior-dev`
- `optimize-codebase-with-senior-dev`
- `create-diagram`

## Access Policy

- **Repository Write**: `false` (analysis-only)
- **Artifact Write**: `true` (audit bundles and optimization reports)
- **External Write**: `false` (no implicit issue publishing)

## Expected Output

- Validated findings bundle with risk classifications and recommended follow-up skill.

## Stopping Conditions

Stop execution with:
- `validated findings`
- `rejected near-misses`
- `coverage limitations`

## Invocation Examples

- **Claude Code**: `@codebase-health-engineer Audit repository for security and maintainability risks.`
- **Cursor**: Invoke subagent `codebase-health-engineer`.
- **Codex**: Enable `.codex/agents/codebase-health-engineer.toml`.

## Known Platform Limitations

- Implementation stages of optimization skills are explicitly disabled within this agent.
