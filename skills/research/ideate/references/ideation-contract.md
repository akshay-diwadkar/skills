# Ideation Contract

This document specifies the exact format of `ideas.md`. The sealer validates
every rule deterministically using standard-library Python only.

## Document structure

```text
# Ideas: <goal>

## 1. Handoff
## 2. Evidence
## 3. Candidate ideas
## 4. Comparison
## 5. Recommendation
## 6. Contradictions and open questions
## 7. Optional downstream action   ← optional; omit when absent
```

Headings must appear in this exact order. No heading may be repeated.

## Section 1: Handoff

Required fields (each must be non-empty):

```text
- State: decision-ready | experiment-first | research-limited
- Goal:
- Scope:
- Non-goals:
- Assumptions:
- Decision horizon:
- Selected source playbooks:
- Research coverage:
- Research limitations:
```

**Allowed states**

| State | When to use |
| --- | --- |
| `decision-ready` | Evidence is sufficient to act on the recommendation |
| `experiment-first` | A decisive experiment must be run before the ranking is reliable |
| `research-limited` | External research was unavailable or severely curtailed |

`research-limited` must not claim strong evidence verification anywhere in
the document. Phrases such as "verified", "confirmed local", or "directly
verified" are prohibited under `research-limited`.

## Section 2: Evidence

### Local evidence (optional)

Omit the `### Local evidence` subsection entirely when no local context was
gathered. When present, include the header row, the separator row, and at
least one data row:

```markdown
| ID | Claim | Source path | Locator | Verification |
| --- | --- | --- | --- | --- |
| L1 | ... | relative/path/to/file | line 42: symbol_name | hash-verified |
```

**Rules**
- IDs must be `L1`, `L2`, … unique and contiguous.
- Source path must resolve beneath the workspace root.
- Locator must be non-empty (line, symbol, section, or key).
- Verification must be non-empty.

### External evidence

The external research status line is required:

```text
External research status: completed | limited | unavailable | user-disabled | local-only
```

Status must agree with evidence:
- `completed` requires at least one external evidence row.
- `local-only` prohibits external evidence rows.

External evidence table (when present):

```markdown
| ID | Finding | Source | Locator | Date/freshness | Relevance |
| --- | --- | --- | --- | --- | --- |
| E1 | ... | url-or-citation | section | 2026-08 | high |
```

External IDs must be `E1`, `E2`, … unique and contiguous.

## Section 3: Candidate ideas

Between 3 and 7 candidates. Each uses heading `### I1. <name>` through
`### I7. <name>`. IDs must be unique and contiguous starting at `I1`.

Each candidate must include all of these fields (non-empty):

```markdown
- Mechanism:
- Why it applies:
- Evidence:
- Expected impact:
- Effort:
- Risk:
- Confidence:
- What would disconfirm it:
- Cheapest decisive experiment:
```

The `Evidence:` field must reference only declared evidence IDs (`L1`, `E2`,
etc.). Every referenced ID must appear in the evidence tables.

## Section 4: Comparison

A Markdown table ranking every candidate exactly once:

```markdown
| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | I2 | high | medium | low | moderate | strong |
```

- Ranks must be unique and contiguous starting at 1.
- Every declared candidate must appear exactly once.
- No candidate may appear more than once.

## Section 5: Recommendation

Required fields:

```markdown
- Provisional lead: I<n> — <name>
- Why it leads:
- Cheapest decisive experiment:
- What could change the ranking:
```

The `Provisional lead` must name the candidate that holds rank 1 in the
comparison table. The sealer verifies this mechanically.

## Section 6: Contradictions and open questions

Free text. `None identified` is a valid value.

## Section 7: Optional downstream action (optional)

Omit this section when no useful downstream action exists. When present,
may name a downstream skill such as `design-codebase`, `optimize-codebase`,
or `plan-change`. Never recommend routing directly to `implement-plan`.

## Prohibited content

- Implementation patches (`diff` or `patch` code blocks with hunk markers).
- Fabricated precision (measurements not supported by cited evidence).
- File-level edit instructions.
- Extra primary artifacts beyond `ideas.md`.
