# Routing Policy

The script is the executable source of truth.

## Decision Semantics

- `primary_skill`: Workflow owning the request (`null` for direct answer).
- `prerequisites`: Workflows required before the primary workflow.
- `follow_up`: Later workflows explicitly requested or required.
- `workflow`: Ordered step objects `{"skill": ..., "description": ...}`.
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

## Execution Intent

`implement-plan` follow-up and approved-plan execution require explicit
execution intent: an imperative at the request start ("Fix the bug."), a
polite imperative ("please update", "can you implement"), or a staged action
("then implement", "and apply"). Wording that merely mentions a change
word ("plan a fix", "refactor plan") is planning or ideation evidence only.
Word boundaries exclude nouns and conjugations; explicit skills and approved
plans keep precedence.

## Overlap Rules

- Ideation → `ideate`, with `design-codebase`/`plan-change`/`implement-plan` follow-up only if requested; never overrides explicit skills or approved plans.
- Unplanned execution requests → `plan-change` with `implement-plan` follow-up (see Execution Intent).
- Structural redesign → `design-codebase` then `plan-change`.
- Unknown risk discovery → `audit-codebase`; named bottlenecks → `optimize-codebase`.
- Audit with issue publication → `audit-codebase` with `raise-issue` follow-up; the diagram routes publication through a "Publish Issues?" decision.
- Prefer one primary skill. Never add heavyweight workflows speculatively.

## Handoff Contract

- `route_handoff` is an inline Markdown document in `result`; no sealed file artifact is produced or claimed.
- Compact by default; detailed guidance is opt-in via `handoff_detail=detailed` (common CLI) or `--handoff detailed` (direct script).
- Persist `route-handoff.md` only at a caller-chosen path outside the repository and installed skill: `handoff_output` (common CLI) or `--output-file` / `--output-dir` (direct script). The resolved destination — output file, or `<output-dir>/route-handoff.md` — is rejected before any write when inside either root, including symlinked parents.
- The handoff embeds the original request text verbatim; only classification uses the normalized text.

## Direct-Answer Boundary

Return `primary_skill: null` and `workflow: []` for explanations, search, summaries, or non-suite requests.
