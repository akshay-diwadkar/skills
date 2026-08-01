# Diagram Output Guide

Use this guide after repository grounding and before building the approved
self-contained HTML diagram. In Plan Mode, model and confirm the artifact only;
do not write, overwrite, save, or verify files.

## Shared-model questions

Resolve purpose, audience, decision, usage, fidelity, output path, entities,
relationships, boundaries, directionality, time, failure paths, omissions, and
the agent afterlife. Default to `narrative-architecture` for mixed audiences;
use `exact-code-graph` only for file/class/function review and
`executive-concept-map` only for business ownership and outcomes. Confirm the
model explicitly before execution. Directory creation, overwrite permission,
plan acceptance, and execution authorization are separate decisions.

Probe concrete scenarios: what touches a new input first, who owns the result,
what remains true after a downstream failure, and what would be misleading if
compressed into one node. Record assumptions, omissions, open questions, and
stable IDs so a future agent can regenerate the chart without the conversation.

## Semantic taxonomy

Node types: `service`, `external-system`, `database`, `queue`, `file`,
`document`, `object-store`, `actor`, `process`, `decision`, `event`, `concept`,
and `failure-state`. Legacy `internal-service` and `data-store` aliases remain
readable but are not for new payloads. Infrastructure normally uses
`external-system` unless a queue, store, or database is clearer.

Edges must use a verb label and a clear direction. Prefer `calls`, `depends-on`,
`produces`, `transforms`, `configures`, or `owns`. Every edge has evidence and
confidence: `observed`, `inferred`, or `stated`. Evidence is `file:line`,
`file:start-end`, or `user-stated`.

## Payload contract

```json
{
  "diagram": {
    "title": "Short title",
    "storageKey": "stable-id",
    "audience": "Who reads it",
    "purpose": "What it explains",
    "fidelity": "narrative-architecture",
    "takeaways": ["One to three decision-relevant statements"],
    "walkthrough": [{"id": "step", "title": "Entry", "nodeIds": ["api"]}],
    "nodes": [{"id": "api", "label": "API", "type": "service"}],
    "edges": [{"sourceId": "api", "targetId": "db", "label": "reads", "evidence": "src/api.py:10", "confidence": "observed"}],
    "clusters": [{"id": "platform", "label": "Platform", "nodeIds": ["api"]}]
  },
  "metadata": {
    "audience": "Who reads it",
    "purpose": "What it explains",
    "fidelity": "narrative-architecture",
    "entities": [], "relationships": [], "assumptions": [],
    "omissions": [], "openQuestions": [], "agentInstructions": []
  }
}
```

IDs are unique, metadata entity IDs match diagram node IDs, and visible and
metadata audience/purpose/fidelity agree. Omit coordinates unless exact layout
is required; if any node has `x`/`y`, every node has both. Use `vertical`
clusters for topological flow and `circular` only for peer groups of at least
three nodes. Keep the visible brief to one to three takeaways and state noisy
details in metadata omissions.

## Build and verify

Build with the bundled renderer, then validate the generated artifact:

```bash
python scripts/build_diagram.py --data /absolute/payload.json \
  --output /absolute/diagram.html --fidelity narrative-architecture
python scripts/validate_diagram.py /absolute/diagram.html
```

Add `--create-dirs` only with directory permission and `--overwrite` only with
replacement permission. The builder embeds the stylesheet and RoughJS runtime;
do not hand-code another renderer or patch generated HTML. The validator checks
template integrity, payload parsing, node/edge contracts, metadata consistency,
coordinates, clusters, and walkthroughs. After validation, inspect readability,
labels, legend, walkthrough, details, drag, pan, zoom, theme, and reset behavior
in a browser. Repair validator errors before presenting the output.
