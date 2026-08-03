# Routing Policy

The agent is the authority; the script is the validator. It never classifies
text or chooses, adds, removes, or reorders skills beyond a stable
topological ordering.

## Authority Boundary

The agent decides whether any skill is needed, which to select, the primary,
exclusions, required capabilities, and intent — read verbatim. The
script validates and returns `{valid, workflow, errors, warnings,
route_handoff}`; `valid: true` means complete, ordered, within authority, not
mandatory execution. No selection means no route-work invocation; the
validator requires ≥1 `--selected-skill`. Authority: read selection,
read facts, validate, emit handoff. Forbidden: classify text, plan, edit
source, publish, commit, push, create a PR, execute the workflow. Fail closed:
any error ⇒ `valid: false`; correct and rerun once, never repaired by
inference.

## Selection Semantics

`selected_skills` is the workflow, one entry per skill, no duplicates;
`primary_skill` must be selected; excluding a required producer is an error,
not a re-route; every `required_capability` needs a selected provider. Facts
(`audit_handoff_available`, `approved_plan_available`,
`issue_context_available`, `repository_navigation_inadequate`) open gates;
selection never does. Pipeline: an earlier selected producer satisfies an
artifact; the fact is the fallback when the producer is not selected.

## Requirements

| Skill | Requires | Satisfied by |
| --- | --- | --- |
| `raise-issue` | `audit-handoff.md` | `audit-codebase` or `audit_handoff_available` |
| `implement-plan` | `docs/plans/*.md` plus approval | `plan-change` and `approved_plan_available` |
| `scope-issue` | GitHub issue context | `issue_context_available` |

All other routed skills (`map-codebase`, `design-codebase`, `plan-change`,
`audit-codebase`, `optimize-codebase`, `diagram-codebase`, `manualize`,
`ideate`) have no artifact requirements. Ordering edges apply between selected
skills only: `audit-codebase`→`raise-issue`;
`design-codebase`/`optimize-codebase`/`scope-issue`/`audit-codebase`→
`plan-change`; `ideate`→`design-codebase`/`plan-change`;
`plan-change`→`implement-plan`; `map-codebase` leads when
`repository_navigation_inadequate=true`.

## Approval Gates

`implement-plan` opens only via `approved_plan_available=true`; only user
approval creates it. `raise-issue` always emits `warn.publication_approval`:
publication authority stays with the user.

## Error Codes

- `selection.*`: `unknown_skill`, `duplicate`, `excluded_unknown`,
  `excluded_primary`, `primary_not_selected`; `exclusion_inert` warns.
- `capability.missing` (no provider), `compatibility.conflict`
  (`implement-plan`+`ideate`, `design-codebase`+`optimize-codebase`),
  `order.cycle` (unorderable).
- `dependency.*`: `missing_artifact`, `excluded_prerequisite`;
  `gate.approval_required`: unsatisfied gate.
- `warn.publication_approval`: any workflow with `raise-issue`.

## Handoff

- `route_handoff` is inline Markdown in `result`; no sealed artifact claimed.
  Compact default; `handoff_detail=detailed` or `--handoff detailed` opts in.
- Persist via `handoff_output` or `--output-file`/`--output-dir`, only outside
  the repository and installed skill; canonical containment (incl. symlinked
  parents) is checked before any write.
- Intent and rationale are echoed verbatim, never analyzed.
