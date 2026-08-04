# Ideate Structural Coverage Rubric

Objective offline pass/fail criteria across 12 structural dimensions:

| # | Dimension | Pass Criteria | Fail Criteria |
| --- | --- | --- | --- |
| 1 | Goal framing | Goal, success measure, and baseline/status quo fields are present and non-empty. | Missing framing fields or empty values. |
| 2 | Evidence quality & traceability | Declared local or external evidence rows (`L1`/`E1`) present in Section 2. | Missing evidence section or undeclared evidence tables. |
| 3 | Candidate structure | At least 3 candidate headings (`I1`, `I2`, `I3`) present. | Fewer than 3 candidate headings. |
| 4 | Mechanism category declared | Every candidate has a non-empty `Mechanism category:` field. | Missing mechanism category field. |
| 5 | Mechanism distinctness | Zero `ideas.duplicate_mechanism_category` diagnostics. | Two or more candidates share identical mechanism categories. |
| 6 | Ranking defensibility | Comparison table present and zero `ideas.recommendation_mismatch` diagnostics. | Rank 1 mismatch or missing comparison table. |
| 7 | Confidence calibration | Zero `ideas.limited_strong_verification` diagnostics. | Overconfident verification assertions under research-limited state. |
| 8 | Decisive experiment completeness | Zero `ideas.decisive_experiment_incomplete` diagnostics. | Experiment missing metric, pass/fail, duration, or effort/cost bounds. |
| 9 | Handling of contradictions | Section 6 is present and non-empty (zero `ideas.empty_section6`). | Missing or empty Section 6 body. |
| 10 | Digest integrity | Zero `ideas.hash_verified_without_digest` diagnostics. | Unverified `hash-verified` labels missing SHA-256 digest. |
| 11 | Actionability | Why it beats rank 2 and rank change conditions fields present. | Missing rank 2 comparison or change conditions. |
| 12 | Structural completeness | Zero total validation diagnostics (`valid == true`). | Any contract validation diagnostic returned. |
