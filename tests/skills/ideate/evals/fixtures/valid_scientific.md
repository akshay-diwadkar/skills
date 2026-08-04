# Ideas: reduce false positives in cell-line screening

## 1. Handoff
- State: experiment-first
- Goal: reduce false positives in cell-line screening
- Success measure: false-positive rate < 5% on a held-out plate
- Baseline / status quo: 12% false-positive rate
- Scope: one assay protocol
- Non-goals: reagent sourcing
- Assumptions: plate layout artifacts are the main driver
- Material unknowns: whether artifact correlates with edge wells
- Decision horizon: before the next screening round
- Decision criteria: specificity gain, protocol change risk
- Selected source playbooks: academic/scientific
- Research coverage: two reviews of assay validation literature
- Research limitations: no access to the original screen dataset
- Research stop condition: stop after 3 sources on validation practice
- Research stop reason: diminishing returns — additional sources repeated the same guidance

## 2. Evidence

### External evidence

External research status: limited

| ID | Finding | Source | Locator | Date/freshness | Relevance |
| --- | --- | --- | --- | --- | --- |
| E1 | Edge effects are a common confound in plate screens | https://example.com/assay-review | § 4 | 2026-05 | medium |

## 3. Candidate ideas

### I1. Randomize well layout
- Mechanism: shuffle treatment positions across plates
- Mechanism category: layout-randomization
- Why it applies: E1 implicates positional confounds
- Evidence: E1 review discusses layout artifacts
- Support basis: evidence-backed: E1
- Decision-criteria fit: high specificity gain, low protocol change risk
- Expected impact: medium
- Assumptions and dependencies: lab workflow tolerates randomization
- Effort: low
- Risk: low
- Confidence: moderate
- What would disconfirm it: artifact persists with fixed layout
- Cheapest decisive experiment: run duplicate plates; metric: false-positive rate; pass/fail: <5%; duration: 1 round; cost/effort: one extra plate

### I2. Normalize by plate position
- Mechanism: apply position-specific correction factors
- Mechanism category: positional-normalization
- Why it applies: known edge effects are correctable
- Evidence: E1 review supports positional corrections
- Support basis: evidence-backed: E1
- Decision-criteria fit: moderate gain, moderate change risk
- Expected impact: medium
- Assumptions and dependencies: enough replicates per position
- Effort: medium
- Risk: medium
- Confidence: low
- What would disconfirm it: no position effect in new data
- Cheapest decisive experiment: fit correction; metric: residual bias; pass/fail: <2%; duration: 2 rounds; cost/effort: medium

### I3. Machine-gated threshold
- Mechanism: learn a per-plate threshold from control wells
- Mechanism category: adaptive-thresholding
- Why it applies: fixed thresholds mislabel noisy wells
- Evidence: unpublished pilot observation
- Support basis: hypothesis
- Decision-criteria fit: unknown gain, high change risk
- Expected impact: high
- Assumptions and dependencies: control wells are representative
- Effort: high
- Risk: high
- Confidence: low
- What would disconfirm it: threshold does not generalize
- Cheapest decisive experiment: cross-validate threshold; metric: false-positive rate; pass/fail: <5%; duration: 3 rounds; cost/effort: high

## 4. Comparison

| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | I1 | medium | low | low | moderate | moderate |
| 2 | I2 | medium | medium | medium | low | moderate |
| 3 | I3 | high | high | high | low | weak |

## 5. Recommendation
- Provisional lead: I1 — Randomize well layout
- Why it leads: lowest-risk path to the target false-positive rate
- Why it beats rank 2: no correction model to maintain
- Cheapest decisive experiment: run duplicate plates; metric: false-positive rate; pass/fail: <5%; duration: 1 round; cost/effort: one extra plate
- What could change the ranking: position-effect magnitude in fresh data
- Conditions that would change the ranking: I2 reaches <3% where I1 stalls above 5%
- How decision criteria were applied: specificity gain was primary, then protocol change risk separated I1 from I2 and I3

## 6. Contradictions and open questions
- Strongest challenge to rank 1: randomization alone may not correct an existing bias
- Baseline / status quo comparison: every option improves on the 12% baseline, but only I1 is testable within one round
- Condition for a different winner: I3 wins if the pilot threshold observation reproduces
- Remaining contradiction or uncertainty: E1 is review-level, not primary data; the decisive experiment is required
