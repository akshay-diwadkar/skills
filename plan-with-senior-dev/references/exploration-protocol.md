# Exploration Protocol

Use this protocol to replace guessing with repo evidence. The goal is not to map the whole repository; it is to find enough truth to constrain the plan.

## Exploration Order

1. Identify the request surface: route, command, component, job, package export, migration, API, or domain document named or implied by the user.
2. Read the nearest source files and tests before broader search.
3. Trace one real call path from entrypoint to output, including validation, persistence, side effects, and error handling when relevant.
4. Find two or three analogous implementations for naming, layering, test style, and failure behavior.
5. Inspect configuration surfaces that can change the plan: env vars, generated files, build scripts, feature flags, schemas, migrations, and deployment hooks.
6. Check domain docs when business language appears: `CONTEXT-MAP.md`, `CONTEXT.md`, and `docs/adr/`.

## Evidence Rules

- Cite discovered facts with `file:line` whenever possible.
- Separate facts from assumptions. Do not let assumptions masquerade as current state.
- Prefer exact local examples over generic best practices.
- If source, tests, and docs disagree, treat that as a planning input, not a nuisance.
- Run non-mutating checks when they can answer a question faster than reading.

## Delegated Exploration

Weaker intelligence subagents can handle bounded evidence-gathering work when the main agent keeps synthesis and decisions.

Good subagent tasks include:

- Locate the entrypoint for a named route, command, component, job, package export, or API.
- Trace one call path from a known entrypoint to output.
- Find two or three analogous implementations or tests.
- Check config surfaces such as env vars, build scripts, generated files, migrations, feature flags, and schemas.
- Summarize relevant `CONTEXT.md`, `CONTEXT-MAP.md`, or `docs/adr/` entries.

Each delegated task must include:

- A narrow prompt with one evidence target.
- Exact search anchors, paths, symbols, or filenames to start from.
- Expected output format: cited bullets with `file:line`, open questions, and contradictions.
- A prohibition on product, architecture, migration, public-interface, or test-strategy decisions.

The main agent must spot-check cited files before using subagent findings in the plan. Treat uncited subagent summaries as leads, not facts.

## Stop Conditions

Stop exploring when all are true:

- The current behavior is clear enough to describe in two to five cited bullets.
- The change boundary is clear: affected entrypoints, data shapes, side effects, and tests.
- Existing patterns show where the new or changed behavior belongs.
- Remaining unknowns are user intent or tradeoffs, not discoverable facts.

For tiny changes, stop after the nearest implementation, one relevant test or command, and any obvious config or type surface.

## Contradictions

When the user request conflicts with code, tests, docs, or established naming:

- State the contradiction plainly.
- Quote the repo fact with a location.
- Ask only for the decision that cannot be derived.
- Recommend the least surprising option based on current behavior unless the user goal clearly requires a change.

## Exploration Anti-Goals

- Do not ask the user where code lives before searching.
- Do not catalog unrelated folders to look thorough.
- Do not read every file in a subsystem when an entrypoint, call path, and analogues are enough.
- Do not plan migrations, public interfaces, or data rewrites without checking the existing schema and compatibility surface.
