# HTML Diagram Output Guide

Use this guide after the questioning framework has reached shared understanding. Build from a structured payload, apply the taxonomy, and embed the agent metadata.

## Section A: Node Type Taxonomy

Every node must be assigned one of these semantic types. The renderer uses `type` for the node color, legend label, and entity-specific shape.

| Type | Shape | Example |
|---|---|---|
| `service` | Rounded service/component box | App backend, auth service, API gateway |
| `external-system` | Cloud/system boundary | Stripe, GitHub, AWS, SendGrid |
| `database` | Cylinder | PostgreSQL, Redis, analytics DB |
| `queue` | Stacked queue cards | SQS, Kafka topic, job queue |
| `file` | Dog-eared file | Config file, source file, artifact |
| `document` | Document page | Runbook, report, generated response |
| `object-store` | Bucket | S3 bucket, blob storage, artifact store |
| `actor` | Actor/person | User, operator, reviewer, team |
| `process` | Rounded process box | Parser, normalizer, build step |
| `decision` | Diamond | Branch, gate, routing decision |
| `event` | Hex/event shape | Domain event, webhook, emitted signal |
| `concept` | Sticky note | Domain boundary, business rule, policy |
| `failure-state` | Warning/octagon | Error handler, timeout, circuit breaker |

Legacy aliases remain supported for compatibility:

| Legacy Type | Canonical Type |
|---|---|
| `internal-service` | `service` |
| `data-store` | `database` |

Infrastructure systems (CI/CD, build servers, deployment platforms, monitoring) map to `external-system` unless they are better represented by a more specific type such as `queue`, `object-store`, or `database`.

## Section B: Edge Type Taxonomy

Every edge must have a verb label describing the relationship:

| Edge Type | Direction Rule | Example |
|---|---|---|
| `calls` | Source invokes a synchronous request on target | `AuthService -> UserDB` |
| `depends-on` | Source requires target to function | `API -> Redis` |
| `produces` | Source creates or emits target | `Pipeline -> Report` |
| `transforms` | Source changes target format or state | `Parser -> AST` |
| `configures` | Source sets parameters for target | `Deploy -> Server` |
| `owns` | Source has lifecycle authority over target | `Team -> Service` |

## Section C: Build Payload

Build generated HTML with the shared template through `/path/to/create-diagram/scripts/build_diagram.py`. Do not hand-edit renderer code for normal create-diagram output. The builder embeds the local stylesheet and RoughJS runtime, so the generated `.html` file is portable and can be opened or served from any directory without copying sibling assets. Generated HTML should differ from `assets/html-diagram-template.html` only in `DIAGRAM_DATA`, `#agent-metadata`, and the builder-managed inline asset blocks.

Payload shape:

```json
{
  "diagram": {
    "title": "Your Diagram Title",
    "storageKey": "unique-diagram-id",
    "audience": "Stakeholders, developers, and managers",
    "purpose": "Explain the architecture decision and operational handoffs",
    "fidelity": "narrative-architecture",
    "takeaways": [
      "Requests enter through the API Gateway before business decisions are applied"
    ],
    "walkthrough": [
      {
        "id": "entry",
        "title": "Request entry",
        "description": "External requests enter through the API Gateway before state is touched.",
        "nodeIds": ["api"]
      }
    ],
    "nodes": [
      {
        "id": "api",
        "label": "API Gateway",
        "type": "service",
        "description": "Entry point for external requests"
      },
      {
        "id": "users",
        "label": "User DB",
        "type": "database",
        "description": "Stores user profiles and sessions"
      }
    ],
    "edges": [
      {
        "sourceId": "api",
        "targetId": "users",
        "label": "reads/writes",
        "evidence": "src/path.ts:10",
        "confidence": "observed"
      }
    ],
    "clusters": [
      {
        "id": "platform",
        "label": "Platform",
        "layout": "vertical",
        "nodeIds": ["api", "users"]
      }
    ]
  },
  "metadata": {
    "audience": "Stakeholders, developers, and managers",
    "purpose": "Explain the architecture decision and operational handoffs",
    "fidelity": "narrative-architecture",
    "entities": [],
    "relationships": [],
    "assumptions": [],
    "omissions": [],
    "openQuestions": [],
    "agentInstructions": []
  }
}
```

Build command:

```bash
python scripts/build_diagram.py --data /absolute/path/to/payload.json --output /absolute/path/to/diagram.html --create-dirs --overwrite
```

Omit `--create-dirs` unless the user has confirmed creating a missing output directory. Omit `--overwrite` unless the user has confirmed replacement. The builder refuses to overwrite an existing file without that flag and refuses to write over the canonical template.

## Section D: `diagram` Rules

- `layout` on a cluster is optional. Use `"vertical"` to stack nodes top-to-bottom in topological order. Use `"circular"` for peer groups with at least 3 nodes.
- `id` values must be unique within the diagram.
- `title` should be short enough to scan in the fixed toolbar.
- `audience`, `purpose`, and `fidelity` are optional but recommended for stakeholder-facing output.
- `fidelity` must be one of `narrative-architecture`, `exact-code-graph`, or `executive-concept-map`.
- `takeaways` is optional. Use 1-3 short sentences.
- `walkthrough` is optional. Each step needs a stable `id`, a human-readable `title`, and non-empty `nodeIds`. Add `description` when the narrative needs explanation.
- Node positions (`x`, `y`) are optional. Prefer omitting them and letting the template auto-layout. If manual positions are used, every node must include both `x` and `y`; mixed or partial manual coordinates are invalid.
- `type` must match the canonical taxonomy in Section A. Legacy aliases render but should not be used for new diagrams.
- `label` on an edge is required and must be a verb describing the relationship.
- `description` is recommended on nodes. It is shown as readable multi-line text in HTML. Recommended length: 15-96 characters.
- `evidence` and `confidence` are required on edges. `confidence` must be `observed`, `inferred`, or `stated`. Use `file:line`, `file:start-end`, or explicit conversation evidence such as `user-stated`.
- `storageKey` is optional. When set, node positions persist in `localStorage`; change the key when the diagram shape changes substantially.
- The HTML viewer includes a toolbar font picker. It is a browser-local display preference only and does not change `DIAGRAM_DATA` or metadata.

## Section E: Agent JSON Metadata

The `metadata` payload becomes the hidden `<script type="application/json" id="agent-metadata">` block. It is invisible to human viewers and gives future agents a durable model.

```json
{
  "audience": "Stakeholders, developers, and managers",
  "purpose": "What this diagram helps a human understand or a developer contribute",
  "fidelity": "narrative-architecture",
  "entities": [
    {
      "id": "api",
      "name": "API Gateway",
      "type": "service",
      "description": "Entry point for external requests",
      "evidence": "src/path/file.ts:10-45"
    }
  ],
  "relationships": [
    {
      "sourceId": "api",
      "targetId": "users",
      "label": "reads/writes",
      "direction": "API Gateway -> User DB",
      "confidence": "observed",
      "evidence": "src/path/file.ts:22"
    }
  ],
  "assumptions": ["List assumptions made during modeling"],
  "omissions": ["What was intentionally left out"],
  "openQuestions": ["Unresolved questions for future design decisions"],
  "agentInstructions": [
    "Keep entity `id` values stable across diagram updates",
    "Match node `id` in DIAGRAM_DATA with `id` in agent-metadata entities"
  ]
}
```

Rules:

- Every entity `id` must match the corresponding `id` in `diagram.nodes`.
- `audience`, `purpose`, and `fidelity` in metadata must match `diagram` when those visible fields are present.
- Relationship `confidence` must be `observed`, `inferred`, or `stated`.
- Relationship `evidence` must cite `file:line`, `file:start-end`, or `user-stated`.
- Empty arrays are allowed for trivial diagrams; add a brief assumption or omission explaining why.

## Section F: Validate Before Presenting

Run:

```bash
python /path/to/create-diagram/scripts/validate_diagram.py <path-to-output.html>
```

The script checks:

- HTML is structurally complete and still matches the canonical template outside data blocks.
- `DIAGRAM_DATA` parses, including normal quoted strings with literal braces.
- Required diagram fields, node types, unique IDs, edge endpoints, edge labels, evidence, confidence, clusters, walkthrough steps, and metadata consistency are valid.
- Manual node coordinates are all-or-none.

If the script exits with code 1, fix all reported errors before presenting. Warnings should be reviewed but do not block presentation.

## Section G: Presentation Readiness

- The title names the system, workflow, or decision being explained.
- The visible brief panel has `audience`, `purpose`, `fidelity`, and no more than 3 `takeaways`.
- `narrative-architecture` is the default fidelity for mixed stakeholder, developer, and manager audiences.
- Exact code graphs and executive concept maps are opt-in.
- The graph shows decision-relevant actors, systems, data flow, ownership, handoffs, and failure paths without exhaustively mapping every low-level dependency.
- Guided walkthrough steps focus the intended narrative path for onboarding, architecture reviews, demos, and incident walkthroughs.
- Omissions are explicit in `metadata.omissions` when noisy implementation details are intentionally compressed.
- The diagram is readable at the default initial readable fit and remains navigable with pan, zoom, font picker, details, guided walkthrough, node dragging, theme toggle, and reset controls.
