---
name: create-diagram
description: Grilling workflow that questions the user to shared understanding, then produces an Excalidraw-style HTML diagram and/or an editable .excalidraw file. Use when the user wants an architecture map, relationship graph, workflow visualization, or any diagram that should be preceded by clarifying questions.
---

# Create Diagram

Use this skill to grill the user with questions until the model is understood, then plan a stakeholder-ready, Excalidraw-style diagram before any file is written. Default to narrative architecture for mixed stakeholder, developer, and manager audiences unless the user explicitly asks for an exact code graph or executive concept map.

## Workflow

1. **Explore before asking:** Inspect the codebase (entrypoints, manifests, schemas, tests) before asking questions the environment can answer.

2. **Load the questioning framework:** Read [question-framework.md](references/question-framework.md) and ask one question at a time to reach shared understanding on purpose, audience, output format, decision to support, narrative scope, entities, relationships, infrastructure context, omissions, and failure paths.

3. **Plan the output files:**
   - Read [html-output-guide.md](references/html-output-guide.md) for node type taxonomy, edge types, metadata schema, and builder payload shape.
   - Read [excalidraw-output-guide.md](references/excalidraw-output-guide.md) when `.excalidraw` output is requested.
   - Ask the user where to create the diagram files before proposing the final plan. When both HTML and `.excalidraw` are requested, ask once; both files are placed in the same directory with the same base name (`.html` and `.excalidraw` extensions). Accept either a full `.html` path or a directory; if the user gives a directory, generate a descriptive kebab-case filename from the diagram title. Recommend the current workspace/project directory when the user has no preference.
   - If the resolved target file already exists, ask before overwriting it. If the target directory does not exist, ask before creating it.
   - Emit exactly one `<proposed_plan>` before any file creation. The plan must include title, purpose, audience, fidelity, output format(s), output location, entities, relationship types, clusters, assumptions, omissions, evidence policy, generated filename behavior, and verification steps.
   - State in the plan that implementation happens only after the user requests execution in a non-Plan turn.

4. **Build only after the plan is approved and execution is allowed:**
   - Create a JSON payload with top-level `diagram` and `metadata` objects. `diagram` becomes `DIAGRAM_DATA`; `metadata` becomes the hidden `<script type="application/json" id="agent-metadata">` block.
   - Populate `diagram` with optional presentation fields (`audience`, `purpose`, `fidelity`, `takeaways`), optional guided walkthrough steps, nodes (id, label, type, optional description), edges (sourceId, targetId, label, evidence, confidence), and clusters.
   - Set each cluster's `layout` to `"vertical"` (stacked top-to-bottom, default) or `"circular"` (orbit around center for peer groups with at least 3 nodes). Prefer `"vertical"` for sequential flows and `"circular"` for clusters whose members have no directional internal edges.
   - Choose a semantic node `type` from the expanded taxonomy in `html-output-guide.md`; the renderer uses it for color, legend label, and entity-specific shape.
   - Populate `description` on each node with a concise 15-96 character explanation. Write complete sentences, not one-word labels.
   - Populate a verb `label`, `evidence`, and `confidence` (`observed`/`inferred`/`stated`) on each edge. Use `file:line` or `file:start-end` for code/doc evidence; use explicit conversation evidence such as `user-stated` for user-stated relationships.
   - Prefer omitting node `x`/`y` positions so auto-layout can run. If manual positions are used, every node must include both `x` and `y`; mixed or partial manual positions are invalid.
   - Build HTML with:
     ```bash
     python scripts/build_diagram.py --data <payload.json> --output <path-to-output.html> --overwrite
     ```
     Omit `--overwrite` unless the user has confirmed replacement.

5. **Validate HTML before verifying:** Run the validation script before opening the HTML file:
   ```bash
   python scripts/validate_diagram.py <path-to-output.html>
   ```
   Fix all reported errors (exit code 1) before proceeding. Warnings should be reviewed but do not block verification.

6. **Generate .excalidraw file (if requested):** After HTML validation passes, run:
   ```bash
   python scripts/generate_excalidraw.py <path-to-output.html>
   ```
   This reads the validated HTML, extracts `DIAGRAM_DATA`, and writes a `.excalidraw` file in the same directory.

7. **Validate .excalidraw file (if generated):** Run:
   ```bash
   python scripts/validate_excalidraw.py <path-to-output.excalidraw>
   ```
   Fix all reported errors (exit code 1) before proceeding.

8. **Verify after building:** Open the HTML file in a browser. Confirm the brief panel renders when presentation fields exist, entity-specific node shapes render, text is readable at initial fit, edges have labels, legend is visible, guided walkthrough starts and advances without changing zoom, and drag/pan/zoom/details/node-drag/theme/reset work during and after walkthrough. If a `.excalidraw` file was generated, also open it in excalidraw.com to confirm all nodes, labels, descriptions, arrows, and clusters render correctly.

## Rules

- One question at a time. Each must include why it matters, your recommendation, and trade-offs.
- Do not write, create, overwrite, save, or verify diagram files while the surrounding collaboration mode is Plan Mode. In Plan Mode, stop after emitting the `<proposed_plan>`.
- Challenge fuzzy terms: "system", "agent", "pipeline", "orchestrator", "service" - make them precise.
- Use concrete scenarios to test the model, especially failure paths and handoffs.
- Do not update CONTEXT.md or ADRs unless the user explicitly asks.
- Do not hand-code standalone SVG, dashboard-style canvases, fixed-size diagram art, or bespoke renderers for normal output. Use the shared Excalidraw-style template and change only `DIAGRAM_DATA` plus `#agent-metadata`.
- Keep the default fidelity as `narrative-architecture`: show decision-relevant actors, systems, data flow, ownership, handoffs, and failure paths without exhaustively mapping every file or dependency.
- Use `exact-code-graph` only when the user asks for developer-only implementation fidelity. Use `executive-concept-map` only when the audience needs business concepts, ownership, outcomes, and risks more than implementation detail.
- The `.excalidraw` file is a derived artifact of the HTML. Do not author it independently. Generate it with `generate_excalidraw.py` after HTML validation passes.
- The `.excalidraw` file must not include walkthrough steps or agent-metadata; those are HTML-only concepts.
- `.excalidraw` edges must be overlap-free: edge strokes and edge labels cannot overlap foreground nodes, node text, other edge strokes, or other edge labels. Source/target anchor contact is allowed only at endpoints; cluster backgrounds may sit behind edges. If `generate_excalidraw.py` cannot route cleanly, fix the diagram data rather than bypassing validation.
