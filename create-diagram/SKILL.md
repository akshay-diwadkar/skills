---
name: create-diagram
description: Grilling workflow that questions the user to shared understanding, then produces an Excalidraw-style HTML diagram. Use when the user wants an architecture map, relationship graph, workflow visualization, or any diagram that should be preceded by clarifying questions.
---

# Create Diagram

Use this skill to grill the user with questions until the model is understood, then plan a stakeholder-ready, Excalidraw-style HTML sketchboard before any file is written. Default to narrative architecture for mixed stakeholder, developer, and manager audiences unless the user explicitly asks for an exact code graph or executive concept map.

## Workflow

1. **Explore before asking:** Inspect the codebase (entrypoints, manifests, schemas, tests) before asking questions the environment can answer.

2. **Load the questioning framework:** Read [question-framework.md](references/question-framework.md) and ask one question at a time to reach shared understanding on purpose, audience, decision to support, narrative scope, entities, relationships, infrastructure context, omissions, and failure paths.

3. **Plan the HTML diagram first:**
   - Read [html-output-guide.md](references/html-output-guide.md) for node type taxonomy, edge types, and metadata schema.
   - Ask the user where to create the HTML diagram before proposing the final plan. Accept either a full `.html` path or a directory; if the user gives a directory, generate a descriptive kebab-case filename from the diagram title. Recommend the current workspace/project directory when the user has no preference.
   - If the resolved target file already exists, ask before overwriting it. If the target directory does not exist, ask before creating it.
   - Emit exactly one `<proposed_plan>` before any file creation. The plan must include title, purpose, audience, fidelity, output location, entities, relationship types, clusters, assumptions, omissions, evidence policy, generated filename behavior, and verification steps.
   - State in the plan that implementation happens only after the user requests execution in a non-Plan turn.

4. **Build only after the plan is approved and execution is allowed:**
    - Copy `assets/html-excalidraw-template.html` and populate only `DIAGRAM_DATA` with optional presentation fields (`audience`, `purpose`, `fidelity`, `takeaways`), optional guided walkthrough steps, nodes (id, label, type, optional description), edges (sourceId, targetId, label, evidence, confidence), and clusters. Set each cluster's `layout` to `"vertical"` (stacked top-to-bottom, default) or `"circular"` (orbit around center for peer groups ≥3 nodes). Prefer `"vertical"` for sequential flows, `"circular"` for clusters whose members have no directional internal edges.
   - Choose a semantic node `type` from the expanded taxonomy in `html-output-guide.md`; the renderer uses it for color, legend label, and entity-specific shape.
   - Populate `description` on each node with a concise 15-96 character explanation - the rendering engine word-wraps up to 3 readable lines below a separator line. Write complete sentences, not one-word labels.
   - Populate a verb `label`, `evidence`, and `confidence` (`observed`/`inferred`/`stated`) on each edge - this renders in the edge hover tooltip. Use `file:line` or `file:start-end` for code/doc evidence; use explicit conversation evidence such as `user-stated` for user-stated relationships.
   - Populate `walkthrough` when the diagram has a meaningful narrative sequence. Each step should have a stable `id`, concise `title`, optional explanatory `description`, and `nodeIds` for the current focus. The renderer dims unrelated nodes and edges during the walkthrough, pans without changing the user's zoom, and infers fallback steps when `walkthrough` is absent.
   - Populate `audience`, `purpose`, and `fidelity` in both `DIAGRAM_DATA` and the hidden `<script type="application/json" id="agent-metadata">` tag. The visible brief panel is for humans; the hidden JSON is for future agents.
   - Populate the rest of the hidden metadata with the structured JSON schema (entities, relationships with evidence and confidence, assumptions, omissions, agent instructions).
   - Save the file only at the user-confirmed output location.

5. **Validate before verifying:** Run the validation script before opening the file:
   ```bash
   python scripts/validate_diagram.py <path-to-output.html>
   ```
   Fix all reported errors (exit code 1) before proceeding. Warnings should be reviewed but do not block verification.

6. **Verify after building:** Open the HTML file in a browser. Confirm the brief panel renders when presentation fields exist, entity-specific node shapes render, text is readable at initial fit, edges have labels, legend is visible, guided walkthrough starts and advances without changing zoom, and drag/pan/zoom/details/node-drag/theme/reset work during and after walkthrough.

## Rules

- One question at a time. Each must include why it matters, your recommendation, and trade-offs.
- Do not write, create, overwrite, save, or verify diagram files while the surrounding collaboration mode is Plan Mode. In Plan Mode, stop after emitting the `<proposed_plan>`.
- Challenge fuzzy terms: "system", "agent", "pipeline", "orchestrator", "service" - make them precise.
- Use concrete scenarios to test the model, especially failure paths and handoffs.
- Do not update CONTEXT.md or ADRs unless the user explicitly asks.
- Do not hand-code standalone SVG, dashboard-style canvases, fixed-size diagram art, or bespoke renderers for normal output. Use the shared Excalidraw-style template and change only `DIAGRAM_DATA` plus `#agent-metadata`.
- Keep the default fidelity as `narrative-architecture`: show decision-relevant actors, systems, data flow, ownership, handoffs, and failure paths without exhaustively mapping every file or dependency.
- Use `exact-code-graph` only when the user asks for developer-only implementation fidelity. Use `executive-concept-map` only when the audience needs business concepts, ownership, outcomes, and risks more than implementation detail.
