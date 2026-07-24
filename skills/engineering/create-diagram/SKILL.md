---
name: create-diagram
description: Create self-contained HTML diagrams of systems, architectures, workflows, and code relationships. Use when the user asks for a diagram, an architecture picture, or a workflow visualization, or wants to communicate a design visually.
---

# Create Diagram

Grill to a shared model, plan the diagram, then build through the bundled template and validators. Default to `narrative-architecture` for mixed stakeholder, developer, and manager audiences unless the user explicitly asks for `exact-code-graph` or `executive-concept-map`.

## Skill Directory Resolution

Execute bundled runtime commands with the active skill directory (the directory containing this `SKILL.md`) set as the process working directory:
- On Claude Code: set `cwd` to `"${CLAUDE_SKILL_DIR}"` (or the active skill directory) if running from an external working directory.
- On other platforms: execute commands with process `cwd` set to the active skill directory.
- Resolve `skill-root` as the directory containing `SKILL.md` and `repo-root` as the absolute target repository path.
- All non-script paths (target repository, plan, output, draft, payload, `.env`, issue JSON, run-dir) passed as arguments MUST be absolute paths.
- Fail closed if `skill-root` or `repo-root` cannot be resolved.
- Never write output or state files relative to the installed skill package directory.

## Workflow

1. **Explore**
   - Inspect the repo before asking questions the environment can answer: docs, entrypoints, manifests, schemas, tests, routes, pipelines, generated artifacts, and existing diagrams.
   - Separate discovered facts from inferences when summarizing what you found.

2. **Question**
   - Read [question-framework.md](references/question-framework.md).
   - Maintain a temporary request-to-evidence gap ledger and ask only questions that cannot be answered from repo inspection or prior user context.
   - Ask up to three related blocking questions per round. Cite the request and repository evidence, explain why the answer changes the diagram, present two to four options when feasible, and recommend one with trade-offs.
   - Incorporate answers, re-explore changed boundaries, and repeat. Do not move to planning until purpose, audience, output location, entities, relationships, omissions, evidence policy, and verification path are known and the resolved model is explicitly confirmed.

3. **Plan**
   - Read [html-output-guide.md](references/html-output-guide.md) for node type taxonomy, edge types, metadata schema, and builder payload shape.
   - Ask the user where to create the HTML diagram before proposing the final plan.
   - Accept either a full `.html` path or a directory. If the user gives a directory, generate a descriptive kebab-case filename from the diagram title.
   - If the resolved target file already exists, ask before overwriting it. If the target directory does not exist, ask before creating it.
   - Treat model alignment, directory creation, and overwrite confirmation as separate permissions; none authorizes building the diagram.
   - Emit exactly one `<proposed_plan>` before any file creation. The plan must include title, purpose, audience, fidelity, output location, entities, relationship types, clusters, assumptions, omissions, evidence policy, generated filename behavior, and verification steps.
   - State in the plan that implementation happens only after the user requests execution in a non-Plan turn when the surrounding collaboration mode is Plan Mode.

4. **Build**
   - Build only after the plan is approved and execution is allowed.
   - Create a JSON payload with top-level `diagram` and `metadata` objects as described in [html-output-guide.md](references/html-output-guide.md).
   - Prefer auto-layout by omitting node `x`/`y`; if manual positions are used, every node must include both `x` and `y`.
   - Run the bundled builder from the active skill directory:
     ```bash
     python scripts/build_diagram.py --data /absolute/path/to/payload.json --output /absolute/path/to/diagram.html --create-dirs --overwrite
     ```
   - The generated HTML is self-contained: the builder embeds the local stylesheet and RoughJS runtime, so the output can be opened or served from any directory without copying sibling assets.
   - Omit `--create-dirs` unless the user has confirmed creating a missing output directory. Omit `--overwrite` unless the user has confirmed replacement.

5. **Validate**
   - Validate HTML before opening it:
     ```bash
     python scripts/validate_diagram.py /absolute/path/to/diagram.html
     ```
   - Fix all reported errors (exit code 1) before proceeding. Warnings should be reviewed but do not block verification.

6. **Verify**
   - Open the HTML file in a browser.
   - Confirm the brief panel renders when presentation fields exist, entity-specific node shapes render, text is readable at initial fit, edges have labels, legend is visible, guided walkthrough starts and advances without changing zoom, and drag/pan/zoom/details/node-drag/theme/reset work during and after walkthrough.

## Rules

- Ask at most three closely related questions per round. Each must include the request/evidence gap, why it matters, two to four options when feasible, your recommendation, and trade-offs.
- Do not write, create, overwrite, save, or verify diagram files while the surrounding collaboration mode is Plan Mode. In Plan Mode, stop after emitting the `<proposed_plan>`.
- Challenge fuzzy terms: "system", "agent", "pipeline", "orchestrator", "service" - make them precise.
- Use concrete scenarios to test the model, especially failure paths and handoffs.
- Do not update CONTEXT.md or ADRs unless the user explicitly asks.
- Do not hand-code standalone SVG, dashboard-style canvases, fixed-size diagram art, or bespoke renderers for normal output. Use the shared HTML template and change only `DIAGRAM_DATA` plus `#agent-metadata`.
- Keep the default fidelity as `narrative-architecture`: show decision-relevant actors, systems, data flow, ownership, handoffs, and failure paths without exhaustively mapping every file or dependency.
- Use `exact-code-graph` only when the user asks for developer-only implementation fidelity. Use `executive-concept-map` only when the audience needs business concepts, ownership, outcomes, and risks more than implementation detail.
