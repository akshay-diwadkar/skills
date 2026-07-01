# HTML Excalidraw-Style Output Guide

Use this guide after the questioning framework has reached shared understanding. Populate the template, apply the taxonomy, and embed the agent metadata.

---

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
| `calls` | Source invokes a synchronous request on Target | `AuthService -> UserDB` |
| `depends-on` | Source requires Target to function | `API -> Redis` |
| `produces` | Source creates or emits Target | `Pipeline -> Report` |
| `transforms` | Source changes Target's format or state | `Parser -> AST` |
| `configures` | Source sets parameters for Target | `Deploy -> Server` |
| `owns` | Source has lifecycle authority over Target | `Team -> Service` |

## Section C: Populating the Template

Copy `assets/html-excalidraw-template.html` and populate two things. Do not build a separate SVG, dashboard, canvas renderer, or hand-authored fixed-size diagram for normal create-diagram output; the shared template is the renderer contract.

### Output Location

Before creating the file, ask the user: "Where should I create the HTML diagram?"

- If the user gives a full `.html` path, save exactly there after confirming overwrite if the file already exists.
- If the user gives a directory, generate a descriptive kebab-case filename from `DIAGRAM_DATA.title`, ending in `.html`.
- If the target directory does not exist, ask before creating it.
- Do not create the diagram in an implicit default location without a user-confirmed path or directory.

### 1. `DIAGRAM_DATA`

```js
const DIAGRAM_DATA = {
  title: "Your Diagram Title",
  storageKey: "unique-diagram-id",
  audience: "Stakeholders, developers, and managers",
  purpose: "Explain the architecture decision and operational handoffs",
  fidelity: "narrative-architecture",
  takeaways: [
    "Requests enter through the API Gateway before business decisions are applied",
    "Durable state lives in User DB; operational recovery is documented in the runbook",
    "External payment risk is isolated behind Stripe integration boundaries"
  ],
  walkthrough: [
    {
      id: "entry",
      title: "Request entry",
      description: "External requests enter through the API Gateway before state is touched.",
      nodeIds: ["api"]
    },
    {
      id: "state",
      title: "Durable state",
      description: "The API reads and writes user profile and session data.",
      nodeIds: ["api", "users"]
    }
  ],
  nodes: [
    { id: "api", label: "API Gateway", type: "service", description: "Entry point for external requests" },
    { id: "users", label: "User DB", type: "database", description: "Stores user profiles and sessions" },
    { id: "runbook", label: "Runbook", type: "document", description: "Explains manual recovery steps" },
  ],
  edges: [
    { sourceId: "api", targetId: "users", label: "reads/writes", evidence: "src/path.ts:10", confidence: "observed" },
  ],
  clusters: [
    { id: "platform", label: "Platform", nodeIds: ["api", "users"] },
  ]
};
```

- `id` values must be unique within the diagram.
- `title` should be short enough to scan in the fixed toolbar. The renderer truncates only the toolbar display when space is tight; the full `DIAGRAM_DATA.title` remains available for metadata, tooltips, and generated filenames.
- `audience` is optional. When present, it appears in the visible brief panel and should name the humans this diagram is for.
- `purpose` is optional but recommended. When present, it appears in the visible brief panel and should state what decision or understanding the diagram supports.
- `fidelity` is optional and must be one of `narrative-architecture`, `exact-code-graph`, or `executive-concept-map`. Default to `narrative-architecture` for mixed stakeholder, developer, and manager audiences.
- `takeaways` is optional. Use 1-3 short sentences; more than 3 takeaways makes the brief panel harder to scan.
- `walkthrough` is optional. Use it when the diagram has a meaningful narrative sequence. Each step needs a stable `id`, a human-readable `title`, an optional `description`, and `nodeIds` for the nodes to focus. During the guided walkthrough, the renderer dims unrelated nodes and edges, highlights edges whose source and target are both in the current step, and pans to the focused nodes without changing the user's zoom level or saved node positions.
- If `walkthrough` is absent or empty, the renderer infers a basic walkthrough from clusters first, then remaining nodes in layout order. Prefer explicit steps for stakeholder-facing artifacts because inferred steps cannot explain why each focus matters.
- Runtime validation warns about duplicate walkthrough IDs, empty walkthrough steps, and walkthrough steps that reference missing node IDs.
- Node positions (`x`, `y`) are optional. For best results, omit them and let the template auto-layout the diagram. Use clusters to define readable horizontal lanes for phases, regions, ownership boundaries, or narrative sections. Auto-layout may shift generated node `y` positions to reduce visible edge overlap while preserving short routes.
- `type` must match one of the canonical types in Section A; legacy aliases still render but should not be used for new diagrams.
- `label` on an edge is required and must be the verb describing the relationship.
- `description` is recommended on nodes. It is shown as a readable multi-line subtitle below a separator line, with the full text available in the hover tooltip. Recommended length: 15-96 characters.
- `evidence` and `confidence` are required on edges. They are shown in the edge hover tooltip. `confidence` must be `observed`, `inferred`, or `stated`. Use `file:line` or `file:start-end` for code/doc claims; use explicit conversation evidence such as `user-stated` for user-stated relationships.
- `storageKey` is optional. When set, node positions persist in `localStorage`; changing the diagram shape or size may require changing the key to avoid restoring old positions.
- The renderer prioritizes readable text and clear routes over fitting every dense diagram into one tiny viewport. `Fit` clamps to a readable scale and relies on pan/zoom for very large graphs.
- Runtime validation warns about duplicate node IDs, unknown node types, dangling edges, missing edge labels, invalid confidence values, missing edge evidence, inconsistent visible/hidden metadata, missing metadata entity IDs, missing cluster members, invalid walkthrough steps, and empty diagrams. Warnings render in the lower-right panel and are logged to the console.
- Keep renderer code from the shared template intact. Generated diagram files should differ only in `DIAGRAM_DATA` and the hidden `#agent-metadata` JSON unless the user explicitly asks to change the renderer itself.

### 2. `#agent-metadata`

Populate the hidden `<script type="application/json" id="agent-metadata">` tag with the JSON schema from Section D. This is invisible to human viewers; only agents reading the HTML source see it.

## Section D: Agent JSON Metadata

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
  "assumptions": [
    "List assumptions made during modeling"
  ],
  "omissions": [
    "What was intentionally left out"
  ],
  "openQuestions": [
    "Unresolved questions for future design decisions"
  ],
  "agentInstructions": [
    "Keep entity `id` values stable across diagram updates",
    "Match node `id` in DIAGRAM_DATA with `id` in agent-metadata entities",
    "Add new entities only when supported by code evidence"
  ]
}
```

### Rules

- Every entity `id` must match the corresponding `id` in `DIAGRAM_DATA.nodes`.
- `audience`, `purpose`, and `fidelity` in `#agent-metadata` must match `DIAGRAM_DATA` when those visible fields are present.
- `confidence` must be one of: `observed` (directly in code), `inferred` (from naming/structure), or `stated` (from user conversation).
- `evidence` must cite `file:line` or `file:start-end` whenever the claim comes from code or docs. Use explicit conversation evidence such as `user-stated` when the relationship is supplied by the user rather than observed in files.
- Empty arrays are allowed for trivial diagrams; add a brief note explaining why.

## Section E: Presentation Readiness

Use this checklist before saving a stakeholder-facing diagram:

- The title is human-readable, concise, and names the system, workflow, or decision being explained.
- The visible brief panel is collapsible and has `audience`, `purpose`, `fidelity`, and no more than 3 `takeaways`.
- `narrative-architecture` is the default fidelity for mixed stakeholder, developer, and manager audiences.
- Exact code graphs are opt-in; use `exact-code-graph` only when the user asks for file/class/function-level dependency fidelity.
- Executive concept maps are opt-in; use `executive-concept-map` only when business concepts, ownership, outcomes, and risks matter more than implementation detail.
- The graph shows decision-relevant actors, systems, data flow, ownership, handoffs, and failure paths without exhaustively mapping every low-level dependency.
- Guided walkthrough steps focus the intended narrative path when the diagram has a natural sequence, especially for onboarding, architecture reviews, demos, and incident walkthroughs.
- Omissions are explicit in `#agent-metadata.omissions`, especially when noisy implementation details are intentionally compressed.
- The diagram is readable at the default `Fit` scale and still navigable with pan, zoom, details, guided walkthrough, node dragging, theme toggle, and reset controls.
