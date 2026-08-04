# Ideation Contract

This document specifies the exact format of `ideas.md`. The sealer validates every rule deterministically using standard-library Python only.

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

Document title must be the first line with a non-empty goal. Headings must appear in exact order, once each.

## Section 1: Handoff

Required non-empty fields:

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

- `decision-ready`: Evidence sufficient for action.
- `experiment-first`: Decisive experiment required before ranking is reliable.
- `research-limited`: External research unavailable/curtailed. Must not claim strong external verification ("verified", "confirmed local", "directly verified"). Local facts may be verified.

## Section 2: Evidence

Evidence IDs (`L1..`, `E1..`) must be declared only inside Section 2 tables.

### Local evidence (optional)

Omit when absent. Required header when present:

```markdown
| ID | Claim | Source path | Locator | Verification |
| --- | --- | --- | --- | --- |
```

Rules: `L1`, `L2`, … unique and contiguous. Source path must resolve under workspace root, exist, and be a regular file. Locator/Verification non-empty. `hash-verified` requires a SHA-256 digest.

### External evidence

Required status line: `External research status: completed | limited | unavailable | user-disabled | local-only`. `completed` requires rows; `local-only` prohibits them. `research-limited` + `completed` is invalid.

Required header when table present:

```markdown
| ID | Finding | Source | Locator | Date/freshness | Relevance |
| --- | --- | --- | --- | --- | --- |
```

External IDs: `E1`, `E2`, … unique and contiguous.

## Section 3: Candidate ideas

3 to 7 candidates (`### I1. <name>` .. `### I7. <name>`). IDs contiguous starting at `I1`. Candidate names and fields non-empty.

Required fields per candidate:

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

Rules:
- `- Evidence:` references declared IDs (`L1`, `E1`). Every declared ID must be cited by at least one candidate.
- Candidates must be mechanism-distinct by unique agent-authored `Mechanism category:`.
- `Cheapest decisive experiment:` must include metric, pass/fail rule, duration bound, and effort/cost bound.

## Section 4: Comparison

Table ranking every candidate exactly once with header:

```markdown
| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |
| --- | --- | --- | --- | --- | --- | --- |
```

Ranks unique and contiguous from 1.

## Section 5: Recommendation

Required fields:

```markdown
- Provisional lead: I<n> — <name>
- Why it leads:
- Why it beats rank 2:
- Cheapest decisive experiment:
- What could change the ranking:
- Conditions that would change the ranking:
```

`Provisional lead` must match Rank 1 candidate. `Cheapest decisive experiment:` must include metric, pass/fail rule, duration, and cost/effort.

## Section 6: Contradictions and open questions

Non-empty body required. `None identified` is valid.

## Section 7: Optional downstream action (optional)

Omit when absent. Must appear after Section 6. May name downstream skills (`design-codebase`, `optimize-codebase`, `plan-change`). Must never route directly to `implement-plan`.

## Prohibited content

Diff/patch code blocks, fabricated precision, file edit instructions, workspace edits, extra primary artifacts beyond `ideas.md`.
