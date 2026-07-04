---
name: create-diagram
description: Diagram creation workflow for architecture diagrams, workflow visualizations, relationship graphs, self-contained HTML artifacts, and diagram requests that need clarifying questions before drawing.
---

# Create Diagram

Grill to a shared model, plan the diagram, then build through the bundled template and validators. Default to `narrative-architecture` for mixed stakeholder, developer, and manager audiences unless the user explicitly asks for `exact-code-graph` or `executive-concept-map`.

## Workflow

1. **Explore**
   - Inspect the repo before asking questions the environment can answer: docs, entrypoints, manifests, schemas, tests, routes, pipelines, generated artifacts, and existing diagrams.
   - Separate discovered facts from inferences when summarizing what you found.

2. **Question**
   - Read [question-framework.md](references/question-framework.md).
   - Ask one question at a time, and ask only questions that cannot be answered from repo inspection or prior user context.
   - Do not move to planning until purpose, audience, output location, entities, relationships, omissions, evidence policy, and verification path are known.

3. **Plan**
   - Read [html-output-guide.md](references/html-output-guide.md) for node type taxonomy, edge types, metadata schema, and builder payload shape.
   - Ask the user where to create the HTML diagram before proposing the final plan.
   - Accept either a full `.html` path or a directory. If the user gives a directory, generate a descriptive kebab-case filename from the diagram title.
   - If the resolved target file already exists, ask before overwriting it. If the target directory does not exist, ask before creating it.
   - Emit exactly one `<proposed_plan>` before any file creation. The plan must include title, purpose, audience, fidelity, output location, entities, relationship types, clusters, assumptions, omissions, evidence policy, generated filename behavior, and verification steps.
   - State in the plan that implementation happens only after the user requests execution in a non-Plan turn when the surrounding collaboration mode is Plan Mode.

4. **Build**
   - Build only after the plan is approved and execution is allowed.
   - Create a JSON payload with top-level `diagram` and `metadata` objects as described in [html-output-guide.md](references/html-output-guide.md).
   - Prefer auto-layout by omitting node `x`/`y`; if manual positions are used, every node must include both `x` and `y`.
   - Run the bundled builder with anchored paths:
     ```bash
     python /path/to/create-diagram/scripts/build_diagram.py --data <payload.json> --output <path-to-output.html> --create-dirs --overwrite
     ```
     PowerShell example: `python C:\path\to\create-diagram\scripts\build_diagram.py --data payload.json --output diagram.html`
     Bash example: `python /path/to/create-diagram/scripts/build_diagram.py --data payload.json --output diagram.html`
   - The generated HTML is self-contained: the builder embeds the local stylesheet and RoughJS runtime, so the output can be opened or served from any directory without copying sibling assets.
   - Omit `--create-dirs` unless the user has confirmed creating a missing output directory. Omit `--overwrite` unless the user has confirmed replacement.

5. **Validate**
   - Validate HTML before opening it:
     ```bash
     python /path/to/create-diagram/scripts/validate_diagram.py <path-to-output.html>
     ```
   - Fix all reported errors (exit code 1) before proceeding. Warnings should be reviewed but do not block verification.

6. **Verify**
   - Open the HTML file in a browser.
   - Confirm the brief panel renders when presentation fields exist, entity-specific node shapes render, text is readable at initial fit, edges have labels, legend is visible, guided walkthrough starts and advances without changing zoom, and drag/pan/zoom/details/node-drag/theme/reset work during and after walkthrough.

## Rules

- Ask one question at a time. Each question must include why it matters, your recommendation, and trade-offs.
- Do not write, create, overwrite, save, or verify diagram files while the surrounding collaboration mode is Plan Mode. In Plan Mode, stop after emitting the `<proposed_plan>`.
- Challenge fuzzy terms: "system", "agent", "pipeline", "orchestrator", "service" - make them precise.
- Use concrete scenarios to test the model, especially failure paths and handoffs.
- Do not update CONTEXT.md or ADRs unless the user explicitly asks.
- Do not hand-code standalone SVG, dashboard-style canvases, fixed-size diagram art, or bespoke renderers for normal output. Use the shared HTML template and change only `DIAGRAM_DATA` plus `#agent-metadata`.
- Keep the default fidelity as `narrative-architecture`: show decision-relevant actors, systems, data flow, ownership, handoffs, and failure paths without exhaustively mapping every file or dependency.
- Use `exact-code-graph` only when the user asks for developer-only implementation fidelity. Use `executive-concept-map` only when the audience needs business concepts, ownership, outcomes, and risks more than implementation detail.
