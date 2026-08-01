---
name: diagram-codebase
description: Create self-contained HTML diagrams of systems, architectures, workflows, and code relationships. Use when the user asks for a diagram, an architecture picture, or a workflow visualization, or wants to communicate a design visually.
version: 3.1.0
metadata:
  invocation: user-invoked
disable-model-invocation: true
user-invocable: true
---

# Diagram Codebase

## Purpose and authority

Ground a shared model, obtain approval, then build one self-contained HTML
diagram with the bundled template. Default to `narrative-architecture`.
Minimum payload: title, fidelity, nodes, labeled edges, and agent metadata.
Use `exact-code-graph` only for code-symbol review and
`executive-concept-map` only for business ownership and outcomes.

Do not create, overwrite, save, or verify diagram files in conversational Plan
Mode. Model approval, directory creation, overwrite permission, and execution
authority are separate decisions. Never hand-code an alternate renderer for
normal output.

## Start

After approval and outside Plan Mode, use absolute paths:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --input fidelity=narrative-architecture --input data=/absolute/payload.json \
  --input output=/absolute/diagram.html --input create_dirs=no \
  --input overwrite=no --format json run
```

Run each returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`. Never change `create_dirs` or `overwrite` to `yes` without
the matching user permission.

## Next-step loop

Inspect repository evidence before asking questions. Follow the phased
[Diagram Output Guide](references/diagram-output-guide.md) until purpose, audience,
fidelity, entities, relationships, omissions, evidence policy, output path, and
verification are confirmed. Emit one approved plan before creating files.

Build the approved `diagram` and `metadata` payload using the taxonomy and
shape in [Diagram Output Guide](references/diagram-output-guide.md). Obtain explicit
permission for a missing directory or existing target, then run each returned
command until validation reaches phase `complete`.

## Completion and recovery

Complete only at phase `complete`, after `validate_diagram.py` passes and the
browser checks in the output guide confirm readability, labels, legend,
walkthrough, details, drag, pan, zoom, theme, and reset behavior.

Repair validator errors before opening the output. Review non-blocking warnings.
If permission, fidelity, or the approved model changes, return to planning and
regenerate the payload; do not patch generated HTML around the builder.
