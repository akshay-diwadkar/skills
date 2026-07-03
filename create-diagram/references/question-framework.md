# Create Diagram Question Framework

Use this framework to reach shared understanding before planning a diagram. Ask one question at a time and wait for the user's answer. In Plan Mode, this framework ends with a `<proposed_plan>`, not a written HTML file.

## Phase 1: Grounding Exploration

When files or a repo are available, inspect before asking:

- Project docs: `README*`, `CONTEXT.md`, `ARCHITECTURE*`, `docs/**`, ADRs.
- Entrypoints and manifests: package files, build configs, app roots, CLI roots, server starts.
- Domain surfaces: route definitions, pipeline/orchestration modules, schemas, tests, examples, sample data.
- Existing diagrams or screenshots.

Summarize discovered facts briefly before asking the first question. Separate facts from inferences.

## Phase 2: Intent

Resolve:

- Purpose: what the diagram must help someone understand or decide.
- Audience: engineer, designer, founder, buyer, stakeholder, operator, manager, or mixed.
- Decision to support: what a stakeholder should be able to approve, challenge, explain, fund, operate, or delegate after seeing the diagram.
- Agent afterlife: what a future agent must infer, modify, or regenerate from the artifact without the original conversation.
- Usage: onboarding, architecture review, debugging, sales/demo, documentation, planning, incident analysis.
- Format: ask "What output format(s) do you need?" Options: HTML, `.excalidraw`, or both. Default recommendation: both. HTML is for sharing and presenting; `.excalidraw` is for future editing and refinement.
- Fidelity: default to `narrative-architecture` for mixed stakeholder, developer, and manager audiences. Use `exact-code-graph` only for file/class/function-level developer reviews. Use `executive-concept-map` only for business concepts, ownership, outcomes, and risks.
- Takeaways: 1-3 concise statements the visible brief panel should make obvious.
- Output location: where the diagram files should be created. Ask once: "Where should I create the diagram file(s)?" When both HTML and `.excalidraw` are requested, both are placed in the same directory with the same base name.

Good first question:

> What decision or understanding should this diagram make obvious to its intended audience?

Include:

- Why this matters.
- My recommendation.
- Trade-offs.

Follow-up when the artifact will be reused:

> What should a future agent be able to understand or safely change from the chart metadata without asking you again?

Default recommendation for mixed audiences:

> I recommend a narrative architecture sketchboard: enough implementation evidence for developers, enough ownership and failure-path context for managers, and enough plain-language purpose for stakeholders.

## Phase 3: Model Extraction

Resolve the subject model:

- Entities: modules, agents, services, jobs, states, users, teams, artifacts, queues, databases, APIs.
- Relationships: ownership, calls, dependencies, data flow, control flow, lifecycle progression, feedback loops.
- Boundaries: what is inside, outside, external, third-party, simulated, or omitted.
- Directionality: who initiates, who observes, who transforms, who stores, who decides.
- Time: build time, runtime, training time, request time, release time, or lifecycle phase.
- Failure paths: retries, timeouts, partial completion, invalid input, stale data, missing artifacts.
- Narrative scope: which actors, systems, decisions, data movement, ownership boundaries, handoffs, and failure paths must be visible for the target audience.
- Omissions: exact implementation details, noisy dependencies, or low-level infrastructure that would distract from the decision being supported.
- Agent model fields: stable entity IDs, relationship IDs, canonical terms, confidence, source evidence, assumptions, omissions, and open questions.

For graph diagrams, also resolve:

- Node scope: files, folders, classes, functions, modules, concepts, artifacts, actors, states, or a deliberate mix.
- Node granularity: every file/class, only public modules, only decision-relevant concepts, or clustered summaries for dense areas.
- Edge taxonomy: import, call, own, depend on, produce, transform, configure, test, document, contain, enable, block, conflict with, or other domain-specific relationships.
- Edge direction: what source and target mean for every edge type.
- Clustering: folder, package, layer, bounded context, team, lifecycle phase, or conceptual region.
- Noise policy: which high-volume edges are hidden, summarized, weighted, or moved into metadata.
- Evidence policy: every edge needs a verb label, confidence (`observed`, `inferred`, or `stated`), and evidence. Use `file:line`, `file:start-end`, or `user-stated`.
- Manual position policy: omit `x`/`y` unless exact placement is required. If any node has manual coordinates, every node must have both `x` and `y`.

Use concrete scenario probes:

- "A new input arrives. What touches it first, and what owns the result?"
- "A downstream step fails. Where is that represented, and what still remains true?"
- "What would be misleading if the diagram compresses this into one box?"

## Phase 4: Infrastructure Context

Resolve the infrastructure that surrounds this codebase: what runs before it, after it, and around it.

- **Build and CI:** "What builds, tests, packages, or containers this code? Where does CI run, and what triggers it?"
- **Provisioning:** "What infrastructure is provisioned before this code runs (databases, queues, storage, networks)? Who manages that provisioning?"
- **Deployment Target:** "Where does this code run in production (hosting platform, Kubernetes, serverless, edge)? Are there staging/QA environments?"
- **Observability:** "How is this system observed - logs, metrics, traces, alerts, dashboards? What platform handles each?"
- **Downstream Consumers:** "What systems consume this code's output - other services, data pipelines, APIs, webhooks, or human-facing UIs? What happens if this system is unavailable?"

If the answer to all questions is "N/A" (solo dev, simple static site), skip to Phase 5. Note differences across environments (dev/staging/prod) and who manages each piece of infrastructure.

## Phase 5: Plan Readiness Gate

Before emitting the `<proposed_plan>`, confirm:

- [ ] Purpose, audience, decision to support, and fidelity are explicit.
- [ ] Output format (HTML, `.excalidraw`, or both) is explicit.
- [ ] Output location is explicit: either a full `.html` path or a directory where a descriptive kebab-case `.html` filename will be generated.
- [ ] `diagram` payload has a stakeholder-ready brief when appropriate: `audience`, `purpose`, `fidelity`, and 1-3 `takeaways`.
- [ ] Scope and exclusions are explicit.
- [ ] Main entities and relationships are named.
- [ ] Edge cases and failure paths are either included or intentionally omitted.
- [ ] Every entity has a stable `id` matching its `id` in `diagram.nodes`.
- [ ] Every relationship has a verb label, evidence, and a confidence level (`observed`, `inferred`, or `stated`).
- [ ] Metadata has `entities`, `relationships`, `assumptions`, `omissions`, `openQuestions`, and `agentInstructions`.
- [ ] Generated HTML will be built with `$skillDir\scripts\build_diagram.py`, validated with `$skillDir\scripts\validate_diagram.py`, and optionally exported/validated with the Excalidraw scripts.

The proposed plan must include title, purpose, audience, fidelity, output location, entities, relationship types, clusters, assumptions, omissions, evidence policy, generated filename behavior, and verification steps. It must also state that implementation happens only after the user requests execution outside Plan Mode.

## Phase 6: Build Gate

Build the HTML diagram only after the plan has been accepted and execution is allowed. Do not write, create, overwrite, save, or verify files while the surrounding collaboration mode is Plan Mode. During the build phase, follow `html-output-guide.md` as the renderer contract and save only at the user-confirmed location.
