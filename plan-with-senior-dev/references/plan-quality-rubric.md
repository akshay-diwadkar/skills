# Plan Quality Rubric

A plan is decision-complete when another engineer or agent can implement it without choosing product behavior, architecture, public interfaces, migration policy, or test strategy.

## Required Qualities

- Title: starts with a specific H1 naming the actual change.
- Outcome: states the user-visible or developer-visible result.
- Current state: cites the existing behavior, structure, or gap.
- Scope: names what changes and what deliberately stays unchanged.
- Approach: follows local patterns or explains the exception.
- Dependency order: starts with foundations, then core behavior, public surface, tests, and docs.
- Interfaces: defines changed APIs, schemas, commands, events, types, outputs, or UI behavior.
- Failure behavior: says what happens on expected errors and edge cases.
- Verification: names tests or commands and expected passing results.
- Rollback: explains how to revert or why rollback is trivial.
- Assumptions: keeps only low-impact assumptions or calls out blocking ones before finalizing.

## Tier Gates

Tiny plans need:

- A specific H1 title.
- One-sentence goal.
- One to three cited current-state facts.
- Exact local change.
- One verification command or manual check.
- Low-impact assumptions only.

Standard plans need:

- A specific H1 title.
- Success criteria.
- Current-state evidence.
- Scope boundaries.
- Dependency-ordered implementation steps.
- Tracer bullet for multi-layer work.
- Failure modes.
- Test strategy.
- Rollback plan.
- Doc updates when domain terms or durable decisions change.

High-risk plans also need:

- A specific H1 title.
- Compatibility and migration notes.
- Explicit rollback for code, data, and external side effects.
- P0/P1/P2 risk register.
- No unresolved P0 risks.
- Pre-mortem findings for real risks, kept compact.

## Pre-Mortem

Before finalizing Standard and High-risk plans, use `references/pre-mortem.md` to look for plan-breaking blind spots. Scale the output to the risk: Tiny plans may only need an assumption sentence, Standard plans should include real P0/P1 findings, and High-risk plans should include compact findings with no unresolved P0s.

## Length Budget

Plan length must scale with task complexity:

- Tiny: 8 to 50 non-empty lines. Use for local, reversible, single-behavior work.
- Standard: 20 to 90 non-empty lines. Use for multi-layer features, bug fixes, and refactors.
- High-risk: 50 to 180 non-empty lines. Use for persisted data, public contracts, security, payments, external integrations, migrations, concurrency, or hard-to-reverse rollout behavior.

Use the lower end when the repo evidence is simple and the change is obvious. Use the upper end only when extra detail prevents real implementation mistakes.

## Script Check

Before finalizing a plan, run the combined plan checker when the plan exists as a draft file or can be piped through stdin:

```bash
python scripts/check_plan.py --tier tiny plan.md
python scripts/check_plan.py --tier standard plan.md
python scripts/check_plan.py --tier high-risk plan.md
python scripts/check_plan.py --tier standard --issue-related plan.md
```

You can optionally separate warnings from errors by passing `--warn` (which exits 0 for warnings), or get structured JSON output using `--format json`.

Pass `--issue-related` for GitHub issue fixes, audit-finding fixes, or repo-fix plans likely to resolve tracked issues. The checker then requires a `Post-Resolution Audit Follow-Up` section that reruns `codebase-issue-auditor`, compares current findings against open audit or GitHub issues, lists resolved candidates with evidence, and requires explicit user approval before closing issues.

The script runs both the shape checker (`check_plan_shape.py`) and the rubric checker (`check_plan_rubric.py`) in sequence:
- The shape checker validates the H1 title, tier-specific sections, reasonable line count, deferred decisions, vague work, weak verification, placeholders, soft commitments, and basic evidence signals.
- The rubric checker looks for evidence, scope boundaries, local-pattern grounding, ordered changes, expected test results, rollback detail, assumption quality, risk handling, compatibility, migration, pre-mortem actionability, and issue follow-up when `--issue-related` is set.

Passing the script is necessary but not sufficient; still apply the rubric below for judgment-heavy issues.


## Final Self-Audit

Before presenting the plan, answer:

- Would two implementers make the same public-interface choices from this plan?
- Are there any "decide later", "consider", "maybe", or "as needed" instructions hiding a real decision?
- Is every current-state claim either cited or marked as an assumption?
- Are tests behavior-focused rather than implementation-focused?
- Does the plan avoid unrelated refactors?
- Does it include enough detail to prevent mistakes without repeating obvious code mechanics?

If any answer fails, explore more, ask a narrower question, or tighten the plan.

## Expected Verification Language

Good verification says:

- What command to run.
- Where to run it.
- What passing output or behavior looks like.
- Which manual scenario matters if automation is not enough.

Weak verification says only "run tests", "add tests", or "verify manually" without naming the behavior being proven.
