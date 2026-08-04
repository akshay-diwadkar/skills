# Ideate Offline Structural Coverage Checker

This evaluation suite provides offline, deterministic structural verification for `ideate` handoff artifacts (`ideas.md`) across objective contract dimensions. It uses local test fixtures (both valid baselines and mutated defect fixtures) with zero LLM API calls or usage costs.

## Structural Dimensions Evaluated

1. **Goal framing:** `Goal:`, `Success measure:`, and `Baseline / status quo:` present in Handoff section.
2. **Evidence traceability:** Evidence section contains declared `L*` or `E*` table rows.
3. **Candidate structure:** At least 3 candidate headings (`### I1.`, `### I2.`, `### I3.`).
4. **Mechanism category declared:** Every candidate includes a `Mechanism category:` field.
5. **Mechanism distinctness:** No two candidates share duplicate mechanism categories (`ideas.duplicate_mechanism_category`).
6. **Ranking defensibility:** Comparison table matches candidates and recommendation lead matches rank 1 (`ideas.recommendation_mismatch`).
7. **Confidence calibration:** State `research-limited` does not claim strong verification (`ideas.limited_strong_verification`).
8. **Decisive experiment completeness:** Candidate & recommendation decisive experiments include metric, pass/fail rule, duration, and cost/effort bounds (`ideas.decisive_experiment_incomplete`).
9. **Contradictions handling:** Section 6 (Contradictions and open questions) is non-empty (`ideas.empty_section6`).
10. **Digest integrity:** `hash-verified` verification labels include valid SHA-256 digests (`ideas.hash_verified_without_digest`).
11. **Actionability:** Recommendation includes explicit rank-2 comparison and change conditions.
12. **Structural completeness:** Handoff draft passes all contract rules with zero diagnostics.

## Running the Checker

Run the deterministic evaluator against any `ideas.md` draft:

```bash
python tests/skills/ideate/evals/score_ideate_evaluation.py --draft /path/to/ideas.md
```
