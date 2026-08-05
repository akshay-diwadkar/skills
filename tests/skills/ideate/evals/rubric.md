# Ideate Structural Coverage Rubric

Objective offline pass/fail criteria across 12 structural dimensions. These checks validate artifact structure and syntax only; they do not measure idea quality, relevance, novelty, or ranking wisdom.

| # | Dimension | Scorer key | Pass Criteria | Fail Criteria |
| --- | --- | --- | --- | --- |
| 1 | Goal framing | `1_goal_framing` | Goal, success measure, and baseline/status quo fields are present. | Missing framing fields. |
| 2 | Support traceability | `2_support_traceability` | Evidence section present and candidates declare `- Support basis:` or declared `L1`/`E1`/`C1` rows exist. | Missing evidence section or support declaration. |
| 3 | Candidate structure | `3_candidate_structure` | At least 3 candidate headings (`I1`, `I2`, `I3`) present. | Fewer than 3 candidate headings. |
| 4 | Mechanism category declared | `4_mechanism_category_declared` | A `Mechanism category:` field is present. | Missing mechanism category field. |
| 5 | Mechanism distinctness | `5_mechanism_distinctness` | Zero `ideas.duplicate_mechanism_category` diagnostics. | Two or more candidates share identical mechanism categories. |
| 6 | Rank-1 lead match | `6_rank1_lead_match` | Comparison table present and zero `ideas.recommendation_mismatch` diagnostics. | Rank 1 mismatch or missing comparison table. |
| 7 | Research-limited verification guard | `7_research_limited_verification_guard` | Zero `ideas.limited_strong_verification` diagnostics. | Strong verification phrases under research-limited state. |
| 8 | Experiment field completeness | `8_experiment_field_completeness` | Zero `ideas.decisive_experiment_incomplete` diagnostics. | Experiment missing metric, pass/fail, duration, or effort/cost bounds. |
| 9 | Adversarial structure | `9_adversarial_structure` | Section 6 contains all four required adversarial bullets and zero related empty-field diagnostics. | Missing or empty adversarial fields. |
| 10 | Digest integrity | `10_digest_integrity` | Zero `ideas.hash_verified_without_digest` / mismatch diagnostics. | Unverified `hash-verified` labels missing or mismatched SHA-256 digest. |
| 11 | Recommendation fields present | `11_recommendation_fields_present` | Rank 2 comparison, rank change conditions, and criteria application fields present. | Missing those recommendation fields. |
| 12 | Structural completeness | `12_structural_completeness` | Zero total validation diagnostics (`valid == true`). | Any contract validation diagnostic returned. |
