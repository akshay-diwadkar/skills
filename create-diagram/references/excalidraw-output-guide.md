# Excalidraw (.excalidraw) Output Guide

Use this guide when the user has requested `.excalidraw` output alone or in addition to HTML. The `.excalidraw` file is always derived from the validated HTML diagram.

## Output Location

The `.excalidraw` file is placed in the same directory as the HTML file with the same base name but a `.excalidraw` extension.

| HTML path | `.excalidraw` path |
|---|---|
| `path/to/my-diagram.html` | `path/to/my-diagram.excalidraw` |

No separate location question is needed. The user's HTML location answer determines both files.

## Shape Mapping

Each `DIAGRAM_DATA` node type maps to an Excalidraw element shape and light-theme color:

| Canonical type | Excalidraw shape | Stroke | Fill | Rounded |
|---|---|---|---|---|
| `service` | rectangle | `#1a7abf` | `#d0e8ff` | Yes |
| `external-system` | rectangle | `#bf7a1a` | `#ffe0b2` | Yes |
| `database` | rectangle | `#1abf4a` | `#d4f5d2` | No |
| `queue` | rectangle | `#2b7fb8` | `#d8f0ff` | Yes |
| `file` | rectangle | `#b7831d` | `#fff2c7` | No |
| `document` | rectangle | `#9a7a2f` | `#fff8df` | No |
| `object-store` | rectangle | `#16856b` | `#d9f7ef` | No |
| `actor` | rectangle | `#9a43b8` | `#f8e0ff` | Yes |
| `process` | rectangle | `#3b78a8` | `#dff0ff` | Yes |
| `decision` | diamond | `#bf6b1a` | `#ffe6d1` | N/A |
| `event` | ellipse | `#5961bf` | `#e5e7ff` | N/A |
| `concept` | rectangle | `#7a1abf` | `#e8d5ff` | No |
| `failure-state` | rectangle | `#bf1a3a` | `#ffd6e0` | No |

Some HTML shapes (cloud, cylinder, dog-ear, note) have no native Excalidraw equivalent. Those types fall back to rectangle and rely on colors and labels for disambiguation.

## What Is Included

- Node shapes with labels and wrapped descriptions.
- Cluster backgrounds and cluster labels.
- Offset edge arrows and edge labels using the same shared geometry helpers as validation/export code.
- Self-loop edges rendered as multi-point arrows.

## Edge Routing Requirement

`.excalidraw` export has a hard overlap-free edge rule. Edge strokes and edge labels must not overlap foreground nodes, node text, other edge strokes, or other edge labels. Source and target anchor contact is allowed only at the arrow endpoints. Cluster background fills are allowed behind edges.

`generate_excalidraw.py` tries deterministic alternate routes before writing the file. If it cannot find a clean route, it exits non-zero and does not write the `.excalidraw` output. `validate_excalidraw.py` independently enforces the same rule on generated or hand-authored files.

## What Is Excluded

- **Walkthrough**: The `.excalidraw` file shows only the static chart. Guided walkthrough steps are HTML-only.
- **Agent metadata**: The hidden `#agent-metadata` JSON is not embedded in the `.excalidraw` file.
- **Dark theme**: The `.excalidraw` file embeds light-theme colors per element.

## Generation Flow

```text
HTML generated and validated
       |
python scripts/generate_excalidraw.py <path-to-diagram.html>
       |
.excalidraw file written to same directory
       |
python scripts/validate_excalidraw.py <path-to-diagram.excalidraw>
```

The generator:

1. Reads the HTML file.
2. Extracts `DIAGRAM_DATA` with the shared parser.
3. Computes or preserves node positions with the shared layout helpers.
4. Selects overlap-free edge routes. If no route is clean, generation fails before writing.
5. Builds cluster backgrounds, node shapes, node text, edge arrows, and edge labels.
6. Writes the `.excalidraw` JSON file next to the HTML file.

## Validation

Run after generation:

```bash
python scripts/validate_excalidraw.py path/to/diagram.excalidraw
```

The validator checks:

- Valid JSON.
- Top-level `type` is `"excalidraw"` and `version` is at least `2`.
- Element IDs are unique.
- Required fields are present: `id`, `type`, `x`, `y`, `width`, `height`.
- Element types are valid Excalidraw types.
- Arrow `points` are valid.
- Arrow bindings, text `containerId`, and `boundElements` references point to existing element IDs.
- Basic `appState` is present.
- Edge strokes and edge labels do not overlap nodes, node text, other edge strokes, or other edge labels.

## Presenting the Result

After validation passes:

1. Open excalidraw.com in a browser.
2. Drag-and-drop the `.excalidraw` file onto the canvas.
3. Confirm all nodes, descriptions, labels, cluster backgrounds, arrows, and edge labels are visible and editable.

Edits are one-way: editing the `.excalidraw` file does not update the HTML source.
