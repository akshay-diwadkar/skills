# Ideate Offline Structural Coverage Checker

This evaluation suite provides offline, deterministic structural verification for `ideate` handoff artifacts (`ideas.md`) across objective contract dimensions. It uses local test fixtures (both valid baselines and mutated defect fixtures) with zero LLM API calls or usage costs.

These checks measure structure and syntax only. They do **not** measure idea quality, relevance, novelty, truth, or ranking wisdom.

## Structural Dimensions Evaluated

1. **Goal framing (`1_goal_framing`):** `Goal:`, `Success measure:`, and `Baseline / status quo:` present in Handoff section.
2. **Support traceability (`2_support_traceability`):** Evidence section present and candidates declare `- Support basis:` or declared `L*` / `E*` / `C*` rows.
3. **Candidate structure (`3_candidate_structure`):** At least 3 candidate headings (`### I1.`, `### I2.`, `### I3.`).
4. **Mechanism category declared (`4_mechanism_category_declared`):** A `Mechanism category:` field is present.
5. **Mechanism distinctness (`5_mechanism_distinctness`):** No duplicate mechanism categories (`ideas.duplicate_mechanism_category`).
6. **Rank-1 lead match (`6_rank1_lead_match`):** Comparison table present and provisional lead matches rank 1 (`ideas.recommendation_mismatch`).
7. **Research-limited verification guard (`7_research_limited_verification_guard`):** State `research-limited` does not claim strong verification (`ideas.limited_strong_verification`).
8. **Experiment field completeness (`8_experiment_field_completeness`):** Decisive experiments include metric, pass/fail, duration, and cost/effort (`ideas.decisive_experiment_incomplete`).
9. **Adversarial structure (`9_adversarial_structure`):** Section 6 contains the four required adversarial bullets.
10. **Digest integrity (`10_digest_integrity`):** `hash-verified` labels include matching SHA-256 digests when required.
11. **Recommendation fields present (`11_recommendation_fields_present`):** Rank-2 comparison, change conditions, and criteria application fields present.
12. **Structural completeness (`12_structural_completeness`):** Draft passes all contract rules with zero diagnostics.

## Running the Checker

Run the deterministic evaluator against any `ideas.md` draft:

```bash
python tests/skills/ideate/evals/score_ideate_evaluation.py --draft /path/to/ideas.md
```
