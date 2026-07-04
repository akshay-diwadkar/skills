# Plan Quality Rubric

A plan is decision-complete when another engineer or agent can implement it without choosing product behavior, architecture, public interfaces, migration policy, rollback policy, or test strategy.

## Required Qualities

- Title: specific H1 naming the actual change.
- Outcome: user-visible or developer-visible result.
- Current state: cited existing behavior, structure, or gap.
- Scope: what changes and what deliberately stays unchanged.
- Reasoning: decomposes the problem, names constraints, rejects weaker approaches.
- Approach: follows local patterns or explains the exception.
- Propagation: maps every changed symbol to direct callers, transitive callers, tests, and config surfaces.
- Constraints: classifies constraints as preserved, modified, or at risk with evidence.
- Interfaces: exact changed signatures, schemas, commands, events, types, outputs, or UI behavior.
- Pseudo-code: branches, loops, error paths, parameters, and return types for non-trivial logic.
- Failure behavior: expected errors and edge cases.
- Test assertions: exact input/output pairs, boundary values, and commands with expected results.
- Devil's Advocate: at least three concrete attack findings or evidence why fewer are material.
- Rollback: revert path or why rollback is trivial.
- Assumptions: only low-impact assumptions, with blocking assumptions resolved before finalizing.

## Tier Gates

Tiny plans need:

- Specific H1 title.
- One-sentence goal.
- One to three cited current-state facts.
- Exact local change, including signatures when changed.
- One verification command or manual check with an exact assertion.
- Compact Devil's Advocate finding or explicit no-material-risk evidence.
- Low-impact assumptions only.

Standard plans need:

- Specific H1 title.
- Success criteria.
- Current-state evidence and contradictions result.
- Scope boundaries, invariants, and blast radius.
- Reasoning summary.
- Change Propagation Map.
- Constraint Verification table.
- Dependency-ordered implementation steps.
- Pseudo-code blocks for logic changes.
- Tracer bullet for multi-layer work.
- Failure modes.
- Test strategy with exact assertions and input/output pairs.
- Devil's Advocate findings with fixes.
- Rollback plan.
- Doc updates when domain terms or durable decisions change.

High-risk plans also need:

- Compatibility and migration notes.
- Explicit rollback for code, data, and external side effects.
- P0/P1/P2 risk register with `Action:` for every P0 and P1.
- Pre-mortem findings for real risks.
- No unresolved P0 risks.

## Pre-Mortem

Before finalizing Standard and High-risk plans, use `references/pre-mortem.md` to find plan-breaking blind spots. Include only real P0/P1 findings and material P2 assumptions. High-risk plans must have no unresolved P0s.

## Devil's Advocate

Before finalizing every plan, use `references/devils-advocate.md`. The plan must either include three concrete findings with fixes or explain why fewer than three attack vectors are material using repo evidence.

## Length Budget

Plan length must scale with task complexity:

- Tiny: 8 to 60 non-empty lines.
- Standard: 30 to 140 non-empty lines.
- High-risk: 60 to 220 non-empty lines.

Use the lower end when evidence is simple and the change is obvious. Use the upper end only when extra detail prevents real implementation mistakes.

## Script Check

Before finalizing a plan, run the combined checker when the plan exists as a draft file or can be piped through stdin:

```bash
python scripts/check_plan.py --tier tiny plan.md
python scripts/check_plan.py --tier standard plan.md
python scripts/check_plan.py --tier high-risk plan.md
```

The checker runs `check_plan_shape.py` and `check_plan_rubric.py`. Passing the script is necessary but not sufficient; still apply this rubric for judgment-heavy gaps.

## Final Self-Audit

- Would two implementers make the same public-interface choices?
- Are there any "decide later", "consider", "maybe", or "as needed" instructions hiding decisions?
- Is every current-state claim cited or marked as an assumption?
- Does every changed symbol have a propagation map entry?
- Does every at-risk constraint have a verification step?
- Do pseudo-code blocks include signatures, parameters, return types, branches, and error paths?
- Are tests behavior-focused with exact assertions?
- Does Devil's Advocate change the plan where needed?
- Does the plan avoid unrelated refactors?

If any answer fails, explore more, ask a narrower question, or tighten the plan.
