# Design Handoff Template

Use this exact heading order. Replace every `REPLACE_*` value with substantive
content. The checker rejects missing, duplicate, reordered, unknown, empty, and
placeholder sections.

Evidence records use this syntax:

```text
- [E-1] source: request | locator: user-request | claim: The requested design pressure.
- [E-2] source: code | locator: relative/path.py:10-24 | anchor: symbol_name | claim: The observed current behavior.
```

Allowed sources are `request`, `code`, `test`, `configuration`, `schema`,
`runtime`, and `external`. Code, test, configuration, and schema evidence must
use a repository-relative `path:start-end` locator. Its optional anchor must
occur inside the cited range. External evidence must use an HTTP(S) URL.

```markdown
# Design Handoff: REPLACE_TITLE

## Evidence Ledger

- [E-1] source: request | locator: user-request | claim: REPLACE_REQUEST_CLAIM
- [E-2] source: code | locator: REPLACE_PATH:REPLACE_LINES | anchor: REPLACE_ANCHOR | claim: REPLACE_REPOSITORY_CLAIM

## Problem & Scope

REPLACE_PRESSURE_SCOPE_AND_EXCLUSIONS [E-1] [E-2]

## Chosen Design & Depth Rationale

- Boundary: REPLACE_CHOSEN_BOUNDARY
- Owner: REPLACE_CHOSEN_OWNER
- Core abstraction: REPLACE_CHOSEN_CORE_ABSTRACTION
- Design: REPLACE_SELECTED_DESIGN
- Hidden details: REPLACE_WHAT_CALLERS_NO_LONGER_NEED_TO_KNOW
- Exposed controls: REPLACE_WHAT_CALLERS_MUST_CONTROL
- Depth rationale: REPLACE_FUNCTIONALITY_TO_INTERFACE_ARGUMENT [E-2]

## Alternatives Considered

### Alternative: REPLACE_ALTERNATIVE_NAME

- Boundary: REPLACE_ALTERNATIVE_BOUNDARY
- Owner: REPLACE_ALTERNATIVE_OWNER
- Core abstraction: REPLACE_DISTINCT_CORE_ABSTRACTION
- Rejected because: REPLACE_STRUCTURAL_REJECTION [E-2]

## Target Interface Contract

| Contract aspect | Today | Proposed | Evidence |
|---|---|---|---|
| Signature | REPLACE_CURRENT_SIGNATURE | REPLACE_PROPOSED_SIGNATURE | [E-2] |
| Defaults | REPLACE_CURRENT_DEFAULTS | REPLACE_PROPOSED_DEFAULTS | [E-2] |
| Nullability | REPLACE_CURRENT_NULLABILITY | REPLACE_PROPOSED_NULLABILITY | [E-2] |
| Caller-visible errors | REPLACE_CURRENT_ERRORS | REPLACE_PROPOSED_ERRORS | [E-2] |

- Error surface direction: REPLACE_WITH_shrink_OR_flat_OR_grow
- Error surface justification: REPLACE_RATIONALE [E-2]

## Generality Justification

REPLACE_GENERAL_OR_INTENTIONALLY_NARROW_JUSTIFICATION_USING_TWO_PRESENT_PATTERNS_AND_THIRD_PATTERN_CONSEQUENCE [E-2]

## Consolidation Considered

REPLACE_CONSOLIDATION_DECISION_OR_EVIDENCED_NOT_APPLICABLE_REASON [E-2]

## Documentation Obligations

REPLACE_NON_SIGNATURE_CALLER_KNOWLEDGE_FOR_PLAN_CHANGE_TO_SCHEDULE [E-2]

## Open Questions for the Planner

REPLACE_ONLY_IMPLEMENTATION_GROUNDING_OR_RECONCILIATION_QUESTIONS_OR_AN_EVIDENCED_NONE_STATEMENT [E-2]
```
