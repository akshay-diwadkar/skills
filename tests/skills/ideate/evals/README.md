# Ideate Offline Structural Coverage Checker

This evaluation suite provides offline, deterministic structural verification for `ideate` handoff artifacts (`ideas.md`) across objective contract dimensions. It uses local test fixtures (valid domain-spanning baselines and mutated defect fixtures) with zero LLM API calls or usage costs.

This checker measures **structure only**. It does not measure relevance, novelty, truth, or ranking wisdom; those are agent obligations, not deterministic contract rules.

## Structural Dimensions Evaluated

1. **Goal framing:** `Goal:`, `Success measure:`, and `Baseline / status quo:` present in Handoff section.
2. **Evidence section:** Section 2 present with an `External research status:` line.
3. **Candidate presence:** At least 3 candidate headings (`### I1.`, `### I2.`, `### I3.`).
4. **Support basis declared:** Every candidate carries a valid `Support basis:` (`ideas.invalid_support_basis`, `ideas.evidence_backed_without_refs`, `ideas.unknown_evidence_reference` absent).
5. **Mechanism distinctness:** No two candidates share duplicate mechanism categories (`ideas.duplicate_mechanism_category`).
6. **Lead match (exact):** Comparison table present and the parsed provisional-lead ID equals rank 1 exactly (`ideas.recommendation_mismatch`).
7. **No overclaimed verification:** State `research-limited` does not claim strong verification (`ideas.limited_strong_verification`).
8. **Decisive experiment completeness:** Candidate and recommendation decisive experiments include metric, pass/fail rule, duration, and cost/effort bounds (`ideas.decisive_experiment_incomplete`).
9. **Challenge substantive:** Section 6 carries the four required challenge fields (`ideas.empty_section6_field`, `ideas.empty_section6` absent).
10. **Digest integrity:** `hash-verified` verification labels include valid SHA-256 digests (`ideas.hash_verified_without_digest`, `ideas.hash_verified_digest_mismatch`).
11. **Criteria applied:** Candidate `Decision-criteria fit:` and recommendation `How decision criteria were applied:` present.
12. **State coherence:** `decision-ready` artifacts carry at least one evidence-backed or assumption-backed candidate (`ideas.unsupported_decision_ready` absent).
13. **Research stop recorded:** `Research stop condition:` and `Research stop reason:` present with a valid reason vocabulary (`ideas.invalid_research_stop_reason` absent).
14. **Structural completeness:** Handoff draft passes all contract rules with zero diagnostics.

## Fixtures

- Valid domain-spanning fixtures: `valid_full.md` (engineering), `valid_scientific.md` (science, experiment-first), `valid_operations_product.md` (operations/product with contextual evidence), `valid_creative_personal.md` (creative/personal, zero-repository), `valid_contextual_evidence.md` (user-provided evidence, non-repository domain).
- Defect fixtures: `missing_support_basis.md`, `decision_ready_all_hypothesis.md`, `missing_challenge_fields.md`, `criteria_not_applied.md`, `missing_research_stop.md`, `lead_i10_mismatch.md`, `missing_experiment_subfields.md`, `empty_section6.md`, `structurally_valid_weak.md`.

## Running the Checker

Run the deterministic evaluator against any `ideas.md` draft:

```bash
python tests/skills/ideate/evals/score_ideate_evaluation.py --draft /path/to/ideas.md
```
