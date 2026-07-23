# Architecture Engineer Agent

Analyze and redesign codebase architecture, module boundaries, coupling, and state ownership without making implementation changes.

## When to Use

- Evaluating or redesigning module boundaries, dependency coupling, or state ownership.
- Assessing whether structural refactoring or design-pattern addition/removal is justified.
- Visualizing complex system architectures, workflows, or module relationships.

## When NOT to Use

- When executing code implementation or applying patches (use `delivery-engineer`).
- For broad defect or vulnerability auditing (use `codebase-health-engineer`).

## Included Skills

- `design-codebase-with-senior-dev`
- `create-diagram`
- `plan-with-senior-dev`

## Access Policy

- **Repository Write**: `false` (read-only enforcement)
- **Artifact Write**: `true` (working assessment artifacts in ignored/temp storage)
- **External Write**: `false` (no git or GitHub mutations)

## Expected Output

- Validated `Codebase Design Assessment` artifact detailing forces, options, tradeoffs, and migration plan.
- Interactive HTML architectural diagram (when visual modeling is requested).

## Stopping Conditions

Stop execution with one of:
- `assessment complete`
- `diagram requested`
- `planning handoff required`
- `blocked on product or contract decision`

## Invocation Examples

- **Claude Code**: `@architecture-engineer Analyze module boundaries between order processing and billing.`
- **Cursor**: Invoke subagent `architecture-engineer` in subagent selector.
- **Codex**: Enable `.codex/agents/architecture-engineer.toml` or run `python tools/agents/install_codex_agents.py --target <project-dir> --write`.

## Known Platform Limitations

- Read-only sandbox mode enforced on Codex and Cursor prevents accidental file modifications.
