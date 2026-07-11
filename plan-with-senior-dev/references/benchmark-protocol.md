# Benchmark Protocol

Use this protocol only to evaluate changes to this skill. Keep task prompts, fixture repositories, and oracle facts separate from candidate outputs.

## Blind A/B Procedure

1. Select the exact weak and strong model IDs and record settings.
2. Generate two baseline outputs per task using the unchanged skill in fresh isolated contexts.
3. Generate two candidate outputs per task with identical prompts and settings.
4. Store outputs outside the fixture repositories so later agents cannot discover them.
5. Randomize baseline/candidate labels with a recorded seed and store the reveal key separately.
6. Give the scorer only the prompt, fixture, oracle, rubric, and anonymized outputs; do not expose the reveal key.
7. Score independently; reveal labels only after scoring is complete.

Do not simulate a weak model by asking a strong model to reason poorly. If two model tiers are unavailable, report cross-model performance as unverified.

## Score

Score 100 points:

- Repository truth: 25.
- Decision completeness: 25.
- Propagation and constraints: 20.
- Executable interfaces and logic: 15.
- Tests, rollback, and risk: 15.

Cap the score at 59 and fail one-shot status for a fabricated repo fact, unsafe public-contract decision, unresolved critical migration risk, or contradictory required behavior.

One-shot means the first final plan, after at most two genuine blocking questions, passes deterministic validation, contains no critical oracle miss, and scores at least 85.

## Acceptance

- Weak cohort: median improvement at least 20 points, median at least 75, one-shot rate at least 75%.
- Strong cohort: median improvement at least 8 points, median at least 90, one-shot rate at least 90%.
- Neither cohort may regress on repository-truth accuracy or add a critical failure.

The deterministic checker verifies structure and cross-links. It does not replace blind judgment of correctness, tradeoffs, or completeness.
