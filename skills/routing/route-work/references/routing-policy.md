# Routing Policy

Use this reference to understand the deterministic classifier. The script is the executable source of truth.

## Decision Semantics

- `primary_skill`: Workflow owning the request (`null` for direct answer).
- `prerequisites`: Workflows required before the primary workflow.
- `follow_up`: Later workflows explicitly requested or required.
- `workflow`: Ordered list of step objects `{"skill": ..., "description": ...}` providing guidance.
- `next_action`: Caller action (`answer_directly`, `invoke_prerequisite`, or `invoke_primary_skill`).
- `allowed_actions` and `forbidden_actions`: Describe router authority, not target skill authority.

## Precedence

Apply the first matching rule:

| Order | Evidence | Route |
| --- | --- | --- |
| 1 | Explicit skill name or chain | Named workflow |
| 2 | Execute approved plan | `implement-plan` |
| 3 | Brainstorming, feature candidates, research options | `ideate` |
| 4 | Publish issues from audit handoff | `raise-issue` |
| 5 | GitHub issue or backlog triage | `scope-issue` |
| 6 | Manual, procedure, runbook, guide, or documentation | `manualize` |
| 7 | Diagram or architecture visualization | `diagram-codebase` |
| 8 | Boundary, dependency direction, or structural design | `design-codebase` |
| 9 | Named performance or build bottleneck | `optimize-codebase` |
| 10 | Broad bug, security, or test gap discovery | `audit-codebase` |
| 11 | Feature, fix, or refactor without approved plan | `plan-change` |
| 12 | Repository orientation | `map-codebase` |
| 13 | No workflow justified | `null` |

## Overlap Rules

- Route research/ideation to `ideate`; add `design-codebase`, `plan-change`, or `implement-plan` as follow-up if requested.
- Route unplanned implementation requests to `plan-change` with `implement-plan` follow-up.
- Route structural redesign to `design-codebase` then `plan-change`.
- Route unknown risk discovery to `audit-codebase`. Route named bottlenecks to `optimize-codebase`.
- Route audit with issue publication to `audit-codebase` with `raise-issue` follow-up.
- Prefer one primary skill. Never add heavyweight workflows speculatively.

## Direct-Answer Boundary

Return `primary_skill: null` and `workflow: []` for general explanations, search, status summaries, or non-suite requests.
