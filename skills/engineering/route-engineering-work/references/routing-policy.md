# Routing Policy

Use this reference only to understand or review the deterministic classifier.
The bundled script is the executable source of truth.

## Decision Semantics

- `primary_skill` is the one workflow that owns the current request. `null`
  means that a direct answer or ordinary tool use is sufficient.
- `prerequisites` contains only workflows that must finish before the primary
  workflow.
- `follow_up` contains only explicitly requested or contract-required later
  workflows.
- `next_action` is `answer_directly`, `invoke_prerequisite`, or
  `invoke_primary_skill`. It describes a caller action; the router never takes
  it.
- `allowed_actions` and `forbidden_actions` describe the router's authority,
  not the authority of the selected workflow.

## Precedence

Apply the first resolved branch:

| Order | Evidence | Route |
| --- | --- | --- |
| 1 | Explicit suite skill name or explicit multi-stage chain | Named workflow, subject to its prerequisites |
| 2 | Execute an available approved or finalized plan | `implement-plan` |
| 3 | GitHub issue, issue inventory, or backlog triage | `scope-issue` |
| 4 | Manual, procedure, runbook, notice, or controlled technical documentation | `manualize` |
| 5 | Diagram, architecture picture, or workflow visualization | `diagram-codebase` |
| 6 | Boundary, dependency direction, state ownership, abstraction, or subsystem design | `design-codebase` |
| 7 | Named performance, build, CI, dependency, maintainability, or developer-experience bottleneck | `optimize-codebase` |
| 8 | Broad or unknown bug, security, performance, test-gap, or maintainability discovery | `audit-codebase` |
| 9 | Feature, fix, refactor, migration, integration, or other source change without an approved plan | `plan-change` |
| 10 | Repository orientation or implementation ownership | `map-codebase` |
| 11 | No suite workflow is justified | `null` |

## Overlap Rules

- Route an implementation request without an approved plan to `plan-change`
  with `implement-plan` as follow-up.
- Route a structural redesign to `design-codebase`, then `plan-change`; add
  `implement-plan` only when execution was requested.
- Route unknown risk discovery to `audit-codebase`. Route a named measurable
  bottleneck to `optimize-codebase`.
- Represent an explicit
  `map-codebase -> plan-change -> implement-plan` request with
  `primary_skill: plan-change`, `map-codebase` as prerequisite, and
  `implement-plan` as follow-up.
- Route actionable audit, design, optimization, and issue handoffs through
  `plan-change`; terminal handoff states stop locally. Add `implement-plan`
  only when execution was requested.
- Prefer one primary skill. Never add a heavyweight workflow merely because it
  might become useful.

## Direct-Answer Boundary

Return `primary_skill: null` for ordinary explanations, exact-string searches,
test or CI status summaries, README summaries, pull-request review/status, and
general engineering questions when the request does not ask for a listed suite
workflow.
