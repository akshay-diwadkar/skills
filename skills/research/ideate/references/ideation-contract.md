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

Document title must be the first line with a non-empty goal.
Headings must appear in this exact order, exactly once each.

## Section 1: Handoff

Required fields (each must be non-empty):

```text
- State: decision-ready | experiment-first | research-limited
- Goal:
- Success measure:
- Baseline / status quo:
- Scope:
- Non-goals:
- Assumptions:
- Material unknowns:
- Decision horizon:
- Decision criteria:
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
```

`research-limited` must not claim strong verification for external evidence.
Phrases like "verified", "confirmed local", or "directly verified" in external
evidence or unsupported certainty are prohibited under `research-limited`.
Legitimately verified local facts are allowed.

Record selected, searched, skipped, unavailable, and user-excluded source classes.

## Section 2: Evidence

Evidence IDs (`L1..`, `E1..`) must be declared only inside Section 2 tables.

### Local evidence (optional)

Omit subsection when no local context was gathered. When present, include exact header:

```markdown
| ID | Claim | Source path | Locator | Verification |
| --- | --- | --- | --- | --- |
| L1 | ... | relative/path/to/file | line 42: symbol_name | truthful-verification |
```

**Rules**
- IDs: `L1`, `L2`, … unique and contiguous.
- Source path: must resolve beneath workspace root, exist, and be a regular file.
- Locator and Verification: non-empty.
- Do not use `hash-verified` unless an actual digest (SHA-256) is provided. Otherwise use truthful terms (e.g. `line-matched`, `inspected`).

### External evidence

Required status line:

```text
External research status: completed | limited | unavailable | user-disabled | local-only
```

Status agreement: `completed` requires external rows; `local-only` prohibits them.
`research-limited` with `completed` is incoherent and invalid.

External evidence table (when present), with exact header:

```markdown
| ID | Finding | Source | Locator | Date/freshness | Relevance |
| --- | --- | --- | --- | --- | --- |
| E1 | ... | url-or-citation | section | 2026-08 | high |
```

External IDs: `E1`, `E2`, … unique and contiguous.

## Section 3: Candidate ideas

Between 3 and 7 candidates (`### I1. <name>` .. `### I7. <name>`). Candidate names and IDs must be non-empty, unique, and contiguous starting at `I1`.

Each candidate requires all fields (non-empty):

```markdown
- Mechanism:
- Mechanism category:
- Why it applies:
- Evidence:
- Expected impact:
- Assumptions and dependencies:
- Effort:
- Risk:
- Confidence:
- What would disconfirm it:
- Cheapest decisive experiment:
```

**Rules**
- Candidate evidence references are parsed strictly from the candidate's `- Evidence:` line. References must cite declared IDs (`L1`, `E1`). Every declared ID must be cited by at least one candidate.
- Every candidate must be mechanism-distinct by an agent-authored `Mechanism category:`. No two candidates may share the same category string.
- `Cheapest decisive experiment:` must include description, metric, pass/fail rule, duration bound, and effort/cost bound.
- Ordinal values (impact, effort, risk, confidence) use anchored ordinal judgments (extensible per goal).

## Section 4: Comparison

Markdown table ranking every candidate exactly once with exact header:

```markdown
| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | I2 | high | medium | low | moderate | strong |
```

- Ranks unique and contiguous from 1. Every declared candidate appears exactly once.

## Section 5: Recommendation

Required fields (each non-empty):

```markdown
- Provisional lead: I<n> — <name>
- Why it leads:
- Why it beats rank 2:
- Cheapest decisive experiment:
- What could change the ranking:
- Conditions that would change the ranking:
```

`Provisional lead` must name the candidate holding rank 1 in Section 4.

## Section 6: Contradictions and open questions

Free text (non-empty). `None identified` is valid.

## Section 7: Optional downstream action (optional)

Omit when absent. Must appear only after Section 6. May name downstream skills (e.g. `design-codebase`, `optimize-codebase`, `plan-change`). Must never route directly to `implement-plan`.

## Prohibited content

- Implementation patches (`diff` or `patch` code blocks with hunk markers).
- Fabricated precision (unsupported numerical measurements).
- File-level edit instructions.
- Workspace modifications or extra primary artifacts beyond `ideas.md`.
