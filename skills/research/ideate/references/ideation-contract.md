# Ideation Contract

The exact `ideas.md` format (contract version 2), enforced by the sealer with
standard-library Python only. **Enforced** rules fail sealing on violation;
**obligation** rules are agent duties too semantic for safe keyword checks.

## Structure (enforced)

`# Ideas: <goal>` (first line, non-empty goal); `## 1. Handoff` … `## 6.
Contradictions and open questions` in exact order, once each; optional
`## 7. Optional downstream action` after Section 6.

## Section 1: Handoff (enforced)

All fields non-empty: State:, Goal:, Success measure:, Baseline / status quo:,
Scope:, Non-goals:, Assumptions:, Material unknowns:, Decision horizon:,
Decision criteria:, Selected source playbooks:, Research coverage:, Research
limitations:, Research stop condition:, Research stop reason:.

`State:` decision-ready = evidence sufficient; experiment-first = decisive
experiment required; research-limited = external research curtailed — no strong
external verification claims (local facts verifiable). `Research stop
condition:` the pre-set condition that ended research. `Research stop reason:`
`condition met | diminishing returns | unavailable sources | user limit`,
optionally `— <explanation>`.

## Section 2: Evidence (enforced)

IDs (`L1..`, `E1..`, `C1..`) declared only in Section 2 tables.

### Local evidence (optional)

Omit when absent; header when present:

```markdown
| ID | Claim | Source path | Locator | Verification |
| --- | --- | --- | --- | --- |
```

`L1..` unique/contiguous; path under workspace root, existing, regular file;
Locator/Verification non-empty; `hash-verified` requires SHA-256 digest.

### Contextual evidence (optional)

Omit when absent; header when present:

```markdown
| ID | Claim | Origin | Verification |
| --- | --- | --- | --- |
```

`C1..` unique/contiguous; `Origin` ∈
`user-provided | direct observation | prior attempt | general knowledge`; cells
non-empty; never path-checked; no effect on `External research status`.

### External evidence

Status: `External research status: completed | limited | unavailable | user-disabled | local-only` — `completed` requires rows, `local-only` prohibits them, `research-limited` + `completed` invalid. Header when present:

```markdown
| ID | Finding | Source | Locator | Date/freshness | Relevance |
| --- | --- | --- | --- | --- | --- |
```

`E1..` unique/contiguous.

## Section 3: Candidate ideas (enforced)

3–7 candidates (`### I1. <name>` …), contiguous from `I1`, names/fields
non-empty. Required per candidate: Mechanism:, Mechanism category:, Why it
applies:, Evidence:, Support basis:, Decision-criteria fit:, Expected impact:,
Assumptions and dependencies:, Effort:, Risk:, Confidence:, What would
disconfirm it:, Cheapest decisive experiment:. `Support basis:` is the single
machine-parsed declaration: `evidence-backed: <declared IDs>` |
`assumption-backed: <assumption>` | `hypothesis`; every declared ID must be
cited.
- `Evidence:` prose, unparsed; never pass off contextual material as a
  repository file or publication (obligation).
- `Decision-criteria fit:` non-empty qualitative statement vs the framed
  criteria; numeric weights discouraged (obligation).
- `Mechanism category:` unique per candidate; identical mechanisms not split
  (obligation).
- `Cheapest decisive experiment:` metric, pass/fail rule, duration bound,
  effort/cost bound.
- `decision-ready` requires ≥1 `evidence-backed` or `assumption-backed`
  candidate; hypotheses-only invalid.

## Section 4: Comparison (enforced)

Every candidate exactly once:

```markdown
| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |
| --- | --- | --- | --- | --- | --- | --- |
```

Ranks unique/contiguous from 1.

## Section 5: Recommendation (enforced)

Provisional lead: I<n> — <name>, Why it leads:, Why it beats rank 2:,
Cheapest decisive experiment:, What could change the ranking:, Conditions that
would change the ranking:, How decision criteria were applied:.

Lead ID must exactly equal rank-1 ID (substring invalid). Decisive experiment:
metric, pass/fail, duration, cost/effort. Criteria statement links Section 1
criteria to the ranking.

## Section 6: Contradictions and open questions (enforced)

Strongest challenge to rank 1:, Baseline / status quo comparison:, Condition
for a different winner:, Remaining contradiction or uncertainty: — all
non-empty.

`Remaining contradiction or uncertainty:` may say none remains only with an
evidence-backed explanation (e.g. `None remaining — both candidates validated
on the same dataset`); bare `None identified.` insufficient.

## Section 7: Optional downstream action (enforced, optional)

Omit when absent; after Section 6; may name skills (`design-codebase`,
`optimize-codebase`, `plan-change`); never `implement-plan`; no diff/patch
blocks.

## Obligations (not enforced)

No fabricated precision. No file-edit or implementation directives or extra
primary artifacts. Honest source selection, research scope, and stop
conditions — the sealer checks only structure and vocabulary.
