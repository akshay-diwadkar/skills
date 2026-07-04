# Exploration Protocol

Use this protocol to replace guessing with repo evidence. The goal is enough truth to constrain the plan, not a full repository census.

## Exploration Order

1. Identify the request surface: route, command, component, job, package export, migration, API, schema, or domain document named or implied by the user.
2. Read the nearest source files and tests before broader search.
3. Trace one real call path from entrypoint to output, including validation, persistence, side effects, and error handling when relevant.
4. Find two or three analogous implementations for naming, layering, test style, and failure behavior.
5. For non-Tiny plans, trace transitive dependencies from changed symbols to the public boundary.
6. Check test coverage for the affected path: existing tests, fixtures, snapshots, mocks, contract tests, and missing scenarios.
7. Inspect configuration surfaces that can change the plan: env vars, generated files, build scripts, feature flags, schemas, migrations, and deployment hooks.
8. Check domain docs when business language appears: `CONTEXT-MAP.md`, `CONTEXT.md`, and `docs/adr/`.
9. Run non-mutating type checks, linters, test discovery, or build commands when they answer current-state questions faster than reading.

## Evidence Rules

- Cite discovered facts with `file:line` whenever possible.
- Separate facts from assumptions.
- Prefer exact local examples over generic best practices.
- Record contradictions between source, tests, docs, config, and user framing.
- Treat contradictions as planning inputs: surface them in Current State and resolve them in Question or Assumptions.

## Delegated Exploration

On non-trivial work, start with bounded delegated evidence gathering when subagents are available. Keep synthesis and decisions in the main agent.

Good delegated tasks:

- Locate an entrypoint for a named route, command, component, job, package export, or API.
- Trace one call path from a known entrypoint to output.
- Find analogous implementations or tests.
- Trace direct and transitive references for one symbol.
- Check config surfaces, generated files, migrations, feature flags, and schemas.
- Summarize relevant `CONTEXT.md`, `CONTEXT-MAP.md`, or `docs/adr/` entries.

Each task must include exact anchors and request cited bullets with `file:line`, open questions, and contradictions. Subagents must not make product, architecture, migration, public-interface, or test-strategy decisions.

The main agent must spot-check cited files before using subagent findings. Treat uncited summaries as leads, not facts.

## Stop Conditions

Stop exploring when all are true:

- Current behavior is clear enough to describe in two to five cited bullets.
- Change boundary is clear: affected entrypoints, data shapes, side effects, tests, and config.
- Existing patterns show where changed behavior belongs.
- Direct and transitive dependency surfaces are known for non-Tiny plans.
- Test coverage and test gaps are known.
- Remaining unknowns are user intent or tradeoffs, not discoverable facts.

For Tiny changes, stop after the nearest implementation, one relevant test or command, and any obvious type/config surface.

## Contradictions Output

Every non-Tiny plan must include one of:

- `Contradictions found: [specific contradiction with evidence]`
- `Contradictions found: none after checking [source/test/docs/config surfaces]`

## Exploration Anti-Goals

- Do not ask the user where code lives before searching.
- Do not catalog unrelated folders to look thorough.
- Do not read every file in a subsystem when an entrypoint, call path, analogues, and propagation are enough.
- Do not plan migrations, public interfaces, or data rewrites without checking schema and compatibility surfaces.
