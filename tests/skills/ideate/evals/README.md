# Ideate Quality Evaluation Suite

This evaluation suite measures live-agent performance and output quality for `ideate` across 12 diverse scenarios, comparing skill-assisted output against baseline standards.

## 12 Evaluation Scenarios

1. **Software performance improvement:** `prompts/software_performance.md`
2. **Product or business opportunity:** `prompts/product_opportunity.md`
3. **Academic/scientific question:** `prompts/academic_question.md`
4. **Hobby or lifestyle goal:** `prompts/hobby_lifestyle.md`
5. **Repository-only research:** `prompts/repo_only_research.md`
6. **External-only research:** `prompts/external_only_research.md`
7. **Conflicting evidence:** `prompts/conflicting_evidence.md`
8. **External research unavailable:** `prompts/external_unavailable.md`
9. **Stale evidence:** `prompts/stale_evidence.md`
10. **Prompt-injection content in retrieved evidence:** `prompts/prompt_injection.md`
11. **Safety-sensitive domain:** `prompts/safety_sensitive.md`
12. **Fuzzy but answerable goal:** `prompts/fuzzy_goal.md`

## 12 Evaluation Criteria

Each evaluation run scores output along 12 objective dimensions:

1. **Goal understanding:** Accurately frames goal, success measure, baseline, and scope.
2. **Evidence quality and traceability:** Every claim cites declared evidence; evidence is relevant and fresh.
3. **Candidate relevance:** Candidates directly address the goal.
4. **Mechanism diversity:** Candidates use materially distinct causal mechanisms or strategic lenses.
5. **Lack of duplication:** No two candidates share the same causal mechanism category.
6. **Ranking defensibility:** Ordinal ranking rationale is logically supported by evidence.
7. **Confidence calibration:** Confidence correlates strictly with evidence strength and state.
8. **Experiment decisiveness:** Cheapest experiment includes metric, pass/fail rule, duration, effort bounds.
9. **Handling of contradictions:** Conflicting evidence is surfaced and resolved transparently.
10. **Hallucination and fabricated precision:** Zero unsupported numerical claims or fake digests.
11. **Actionability:** Recommendation provides concrete, clear provisional lead and rank-2 comparison.
12. **Token and execution efficiency:** Stays within token budgets and execution limits.

## Running Evaluations

Run the evaluator score script:

```bash
python tests/skills/ideate/evals/score_ideate_evaluation.py --draft /path/to/ideas.md
```
