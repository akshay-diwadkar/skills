# Design Handoff Template

Use this exact heading order. Replace every `REPLACE_*` value with substantive
content. The sealer rejects missing, duplicate, reordered, unknown, empty, and
placeholder sections.

Evidence records use this syntax:

```text
- [E-1] source: request | locator: user-request | claim: The requested design pressure.
- [E-2] source: code | locator: relative/path.py:10-24 | anchor: symbol_name | sha256: 64_lowercase_hex_characters | claim: The observed current behavior.
```

Allowed sources are `request`, `code`, `test`, `configuration`, `schema`,
`runtime`, and `external`. Code, test, configuration, and schema evidence must
use a repository-relative `path:start-end` locator. Their optional `sha256`
binds the exact inclusive line range using UTF-8 text, LF joins, and one final
LF; sealing backfills it when omitted. The optional anchor must occur
inside the cited range. Other source types must not carry `sha256`. External
evidence must use an HTTP(S) URL. At least one structurally distinct
alternative must cite an evidence record not cited by the chosen rationale.

```markdown
# Design Handoff: REPLACE_TITLE

## Evidence Ledger

- [E-1] source: request | locator: user-request | claim: REPLACE_REQUEST_CLAIM
- [E-2] source: code | locator: REPLACE_PATH:REPLACE_LINES | anchor: REPLACE_ANCHOR | sha256: REPLACE_OPTIONAL_CURRENT_EXCERPT_HASH | claim: REPLACE_REPOSITORY_CLAIM
- [E-3] source: code | locator: REPLACE_ALTERNATIVE_PATH:REPLACE_LINES | anchor: REPLACE_ALTERNATIVE_ANCHOR | sha256: REPLACE_OPTIONAL_CURRENT_EXCERPT_HASH | claim: REPLACE_ALTERNATIVE_GROUNDING

## Problem & Scope

REPLACE_PRESSURE_SCOPE_AND_EXCLUSIONS [E-1] [E-2]

## Chosen Design & Depth Rationale

- Boundary: REPLACE_CHOSEN_BOUNDARY [E-2]
- Owner: REPLACE_CHOSEN_OWNER [E-2]
- Core abstraction: REPLACE_CHOSEN_CORE_ABSTRACTION [E-2]
- Coupling direction: REPLACE_DEPENDENCY_KNOWLEDGE_FROM_AND_TO [E-2]
- Design: REPLACE_SELECTED_DESIGN [E-2]
- Hidden details: REPLACE_WHAT_CALLERS_NO_LONGER_NEED_TO_KNOW [E-2]
- Exposed controls: REPLACE_WHAT_CALLERS_MUST_CONTROL [E-2]
- Depth rationale: REPLACE_FUNCTIONALITY_TO_INTERFACE_ARGUMENT [E-2]

## Alternatives Considered

### Alternative: REPLACE_ALTERNATIVE_NAME

- Boundary: REPLACE_ALTERNATIVE_BOUNDARY [E-3]
- Owner: REPLACE_ALTERNATIVE_OWNER [E-3]
- Core abstraction: REPLACE_DISTINCT_CORE_ABSTRACTION [E-3]
- Coupling direction: REPLACE_ALTERNATIVE_DEPENDENCY_KNOWLEDGE_FROM_AND_TO [E-3]
- Rejected because: REPLACE_STRUCTURAL_REJECTION [E-3]

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
