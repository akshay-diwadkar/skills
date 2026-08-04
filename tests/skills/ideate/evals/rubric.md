# Ideate Structural Coverage Rubric

Objective offline pass/fail criteria across 14 structural dimensions. Structural only: no dimension claims to measure relevance, novelty, truth, or ranking wisdom.

| # | Dimension | Pass Criteria | Fail Criteria |
| --- | --- | --- | --- |
| 1 | Goal framing | Goal, success measure, and baseline/status quo fields are present and non-empty. | Missing framing fields or empty values. |
| 2 | Evidence section | Section 2 present with an external research status line. | Missing evidence section or status line. |
| 3 | Candidate presence | At least 3 candidate headings (`I1`, `I2`, `I3`) present. | Fewer than 3 candidate headings. |
| 4 | Support basis declared | Every candidate has a valid support basis; zero `ideas.invalid_support_basis`, `ideas.evidence_backed_without_refs`, `ideas.unknown_evidence_reference`. | Missing, malformed, or unreferenced support basis. |
| 5 | Mechanism distinctness | Zero `ideas.duplicate_mechanism_category` diagnostics. | Two or more candidates share identical mechanism categories. |
| 6 | Lead match (exact) | Comparison table present and zero `ideas.recommendation_mismatch`; parsed lead ID equals rank 1 exactly. | Lead ID mismatch, including substring collisions such as `I10` for `I1`. |
| 7 | No overclaimed verification | Zero `ideas.limited_strong_verification` diagnostics. | Overconfident verification assertions under research-limited state. |
| 8 | Decisive experiment completeness | Zero `ideas.decisive_experiment_incomplete` diagnostics. | Experiment missing metric, pass/fail, duration, or effort/cost bounds. |
| 9 | Challenge substantive | All four Section 6 challenge fields present; zero `ideas.empty_section6_field`, `ideas.empty_section6`. | Missing challenge fields or bare `None identified.`. |
| 10 | Digest integrity | Zero `ideas.hash_verified_without_digest`, `ideas.hash_verified_digest_mismatch`. | Unverified `hash-verified` labels missing SHA-256 digest. |
| 11 | Criteria applied | Candidate `Decision-criteria fit:` and recommendation `How decision criteria were applied:` present. | Missing criteria fit or application fields. |
| 12 | State coherence | Zero `ideas.unsupported_decision_ready`. | decision-ready artifact supported only by hypotheses. |
| 13 | Research stop recorded | Stop condition and reason present; zero `ideas.invalid_research_stop_reason`. | Missing stop fields or out-of-vocabulary reason. |
| 14 | Structural completeness | Zero total validation diagnostics (`valid == true`). | Any contract validation diagnostic returned. |
