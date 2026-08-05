# Ideate Structural Coverage Rubric

Objective offline pass/fail criteria across 12 structural dimensions. These checks validate artifact structure and syntax only; they do not measure idea quality, relevance, novelty, or ranking wisdom.

| # | Dimension | Pass Criteria | Fail Criteria |
| --- | --- | --- | --- |
| 1 | Goal framing | Goal, success measure, and baseline/status quo fields are present and non-empty. | Missing framing fields or empty values. |
| 2 | Support traceability | Evidence section present and candidates declare `- Support basis:` or declared `L1`/`E1`/`C1` rows exist. | Missing evidence section or support declaration. |
| 3 | Candidate structure | At least 3 candidate headings (`I1`, `I2`, `I3`) present. | Fewer than 3 candidate headings. |
| 4 | Mechanism category declared | Every candidate has a non-empty `Mechanism category:` field. | Missing mechanism category field. |
| 5 | Mechanism distinctness | Zero `ideas.duplicate_mechanism_category` diagnostics. | Two or more candidates share identical mechanism categories. |
| 6 | Ranking defensibility | Comparison table present and zero `ideas.recommendation_mismatch` diagnostics. | Rank 1 mismatch or missing comparison table. |
| 7 | Confidence calibration | Zero `ideas.limited_strong_verification` diagnostics. | Overconfident verification assertions under research-limited state. |
| 8 | Decisive experiment completeness | Zero `ideas.decisive_experiment_incomplete` diagnostics. | Experiment missing metric, pass/fail, duration, or effort/cost bounds. |
| 9 | Adversarial structure | Section 6 contains all four required adversarial bullets and zero `ideas.missing_adversarial_field` / `ideas.empty_section6` diagnostics. | Missing or empty adversarial fields. |
| 10 | Digest integrity | Zero `ideas.hash_verified_without_digest` diagnostics. | Unverified `hash-verified` labels missing SHA-256 digest. |
| 11 | Actionability | Rank 2 comparison, rank change conditions, and criteria application fields present. | Missing rank 2 comparison, change conditions, or criteria application. |
| 12 | Structural completeness | Zero total validation diagnostics (`valid == true`). | Any contract validation diagnostic returned. |
