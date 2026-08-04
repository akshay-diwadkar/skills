# Ideate Quality Judging Rubric

Objective pass/fail criteria across 12 dimensions:

| # | Dimension | Pass Criteria | Fail Criteria |
| --- | --- | --- | --- |
| 1 | Goal understanding | Goal, success measure, baseline, scope, and non-goals are explicitly framed. | Missing framing fields or generic placeholders. |
| 2 | Evidence quality & traceability | All candidate evidence fields reference declared L*/E* IDs; evidence freshness/relevance recorded. | Undeclared evidence citations or missing evidence table entries. |
| 3 | Candidate relevance | 3–7 candidates generated; all directly address the stated goal. | <3 or >7 candidates; candidates irrelevant to goal. |
| 4 | Mechanism diversity | Candidates explore distinct causal mechanisms or strategic lenses. | All candidates share the same approach. |
| 5 | Lack of duplication | Every candidate has a unique Mechanism category string. | Two or more candidates share identical mechanism categories. |
| 6 | Ranking defensibility | Rank 1 lead is supported by comparison table and explicit rationale vs Rank 2. | Rank 1 mismatch or unsupported ranking claims. |
| 7 | Confidence calibration | Confidence matches evidence strength; `research-limited` has no strong verification claims. | Overconfident assertions under limited research. |
| 8 | Experiment decisiveness | Cheapest experiment has metric, pass/fail rule, duration bound, effort bound. | Vague experiment description without pass/fail rule. |
| 9 | Handling of contradictions | Section 6 identifies contradictions or explicitly records `None identified`. | Ignores known conflicting evidence in retrieved sources. |
| 10 | Hallucination / fake precision | Zero unsupported numerical claims or unverified `hash-verified` labels. | Fabricated statistics or unverified hash labels. |
| 11 | Actionability | Clear provisional lead, why it beats rank 2, and rank change conditions. | Vague recommendation or missing rank 2 comparison. |
| 12 | Token & execution efficiency | Handoff document remains concise and within context token limits. | Bloated draft exceeding context budget. |
