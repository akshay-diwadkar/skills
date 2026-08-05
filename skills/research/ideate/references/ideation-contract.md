# Ideation Contract (v2)

Exact `ideas.md` format. Python enforces structure and syntax only; idea quality, relevance, novelty, and truthful prose remain agent obligations.

## Structure

```text
# Ideas: <goal>
## 1. Handoff
## 2. Evidence
## 3. Candidate ideas
## 4. Comparison
## 5. Recommendation
## 6. Contradictions and open questions
## 7. Optional downstream action   ← omit when absent
```

Title first line, non-empty goal. Headings in order, once each.

## Deterministic rules

### Handoff

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
- Research stop condition:
- Research stop reason:
```

`Research stop reason:` begins with `condition met`, `diminishing returns`, `unavailable sources`, or `user limit` (optional ` — note`). `decision-ready` rank 1 cannot use `hypothesis:` support. `research-limited` forbids strong external verification phrases in external evidence.

### Evidence

IDs declared only in Section 2: `L*` local (optional), `E*` external, `C*` contextual (optional).

Local header: `| ID | Claim | Source path | Locator | Verification |` — path under workspace, regular file, non-empty locator/verification; `hash-verified` needs SHA-256.

External status: `completed | limited | unavailable | user-disabled | local-only`. Header: `| ID | Finding | Source | Locator | Date/freshness | Relevance |`.

Contextual header: `| ID | Claim | Source description | Locator | Verification |` — user facts not repo files or external publications.

All ID sets unique and contiguous.

### Candidates

3–7 candidates: `### I1. <name>` .. `### I7. <name>`. Required fields:

```text
- Mechanism:
- Mechanism category:
- Why it applies:
- Support basis:
- Decision-criteria fit:
- Expected impact:
- Assumptions and dependencies:
- Effort:
- Risk:
- Confidence:
- What would disconfirm it:
- Cheapest decisive experiment:
```

Support basis (exact prefix):

```text
- Support basis: evidence-backed: L1, E1, C1
- Support basis: assumption-backed: <material assumption>
- Support basis: hypothesis: <unverified claim>
```

Every declared ID cited by ≥1 candidate. Mechanism categories distinct. Decisive experiment needs metric, pass/fail, duration, cost/effort bounds.

### Comparison

`| Rank | Candidate | Impact | Effort | Risk | Confidence | Support strength |` — rank every candidate once, contiguous ranks.

### Recommendation

```text
- Provisional lead: I<n> — <name>
- Why it leads:
- Why it beats rank 2:
- How decision criteria were applied:
- Cheapest decisive experiment:
- What could change the ranking:
- Conditions that would change the ranking:
```

Leading candidate ID must exactly match rank 1 (`I1` ≠ `I10`).

### Section 6

```text
- Strongest challenge to rank 1:
- Baseline comparison:
- Alternate winner condition:
- Remaining uncertainty:
```

### Section 7

Optional. Never route to `implement-plan`.

### Prohibited (deterministic)

Diff/patch code blocks.

### Receipt

`<!-- ideas-handoff: 2; sha256: <digest> -->`

## Agent obligations (not machine-judged)

Truthful support prose, substantive criteria application and adversarial reasoning, honest research-stop recording, no fabricated precision, no file-edit instructions in artifact prose.
