---
name: plan-with-senior-dev
description: Produce codebase-grounded, decision-complete implementation plans through focused exploration, plan-shaping questions, existing-pattern alignment, domain-doc judgment, and concrete verification.
---

# Plan With Senior Dev

Turn an ambiguous implementation request into a plan another engineer or agent can execute without choosing product behavior, architecture, public interfaces, migration policy, or test strategy.

The skill is intentionally lean. Do the thinking in the current repo, keep the final plan compact, and only add detail that prevents a likely implementation mistake.

## Reference Routing

Read these files only when they match the task risk or ambiguity:

- `references/exploration-protocol.md`: before asking questions on non-trivial codebase work, or when current-state evidence is thin.
- `references/question-strategy.md`: when the prompt has unresolved product, scope, interface, migration, terminology, or test choices.
- `references/grilling-protocol.md`: compact pressure-test and exit-criteria checklist used during §2.
- `references/plan-quality-rubric.md`: before finalizing plans, choosing plan length, or running `scripts/check_plan.py`.
- `references/pre-mortem.md`: before finalizing Standard or High-risk plans, risky migrations, public contracts, integrations, rollback-sensitive changes, or plans that feel optimistic.
- `references/anti-patterns.md`: when the plan feels vague, overbuilt, under-evidenced, or likely to leave choices to the implementer.

## Core Contract

Always:

- Explore the repo before asking questions, unless the prompt itself is contradictory and cannot be explored.
- Separate discovered facts from assumptions; cite codebase facts with `file:line` whenever possible.
- Prefer existing local patterns, helpers, tests, and architecture over new abstractions.
- Ask only questions whose answers change scope, behavior, architecture, risk, docs, or tests.
- Produce a decision-complete plan with concrete verification commands and expected results.
- Keep domain docs focused: `CONTEXT.md` is glossary-only; ADRs are for durable tradeoffs.

Never:

- Ask the user for facts that code, tests, docs, or config can answer.
- Invent provider/factory/interface layers unless the repo already uses them or two concrete cases justify them.
- Present a plan with unresolved product, architecture, migration, or public-interface choices.
- Use hedging language such as "might want to", "could potentially", or "consider implementing".
- End the plan by asking permission to proceed.

## Runtime Flow

### 1. Explore

Build enough current-state evidence to constrain the plan.

Check, as relevant:

- Domain docs: `CONTEXT-MAP.md`, `CONTEXT.md`, and `docs/adr/`.
- Entrypoints: routes, commands, jobs, UI flows, public APIs, or package exports.
- Call path: the main flow from entrypoint through validation, persistence, side effects, and output.
- Analogous patterns: two or three nearby examples for structure, naming, errors, and tests.
- Test landscape: existing test files, runner, commands, setup data, mocks, and coverage gaps.
- Config/build surfaces: env vars, generated files, migrations, codegen, and deployment hooks.
- Contradictions: where the request conflicts with code, docs, tests, or established conventions.

Do not over-map tiny changes. For a single-file local change, one cited current-state finding plus the relevant test command is enough.

### 2. Grill to Shared Understanding

After exploration, run a design-tree walk before planning. The goal is shared understanding of every decision branch, not a large transcript of questions.

**Procedure:**

1. State the current hypothesis in one paragraph.
2. Identify the root decision that determines the next branch.
3. Ask one question at a time with this format:

```text
Question: [specific decision]
Recommended answer: [default], because [repo evidence or risk]
Why it matters: [what changes if the answer differs]
```

4. After the user answers, update the hypothesis and move to the next dependent decision.
5. For each major decision, test at least one concrete scenario: happy path, boundary, failure, and compatibility — preferring scenarios that force a boundary between two domain concepts or architectural responsibilities.
6. Stop when every branch has an owner decision, a repo-backed default, or an explicit out-of-scope call.

**Shared-Understanding Exit Criteria:**

The grilling session is done when all are true:
- Goal and success criteria are concrete.
- Important terms have agreed meanings and clear boundaries.
- Referenced docs or prior decisions have been checked or marked as assumptions.
- In-scope and out-of-scope behavior are named.
- Public interfaces and data shapes are decided or explicitly unchanged.
- Edge cases have expected behavior.
- Migration, compatibility, rollback, and docs decisions are settled when relevant.
- The test strategy proves the risky behavior.

If any item remains unresolved and matters to implementation, do not proceed to planning.

### 3. Plan

Choose the smallest plan that satisfies the user's goal and fits the repo.

Order changes by dependency, not by filename:

1. Foundations with no local dependencies.
2. Core behavior.
3. Public surface or orchestration.
4. Tests and verification.
5. Docs, migrations, or release notes when needed.

For Standard and High-risk work, include a tracer bullet: the smallest vertical slice that proves the approach end to end before the rest is filled in.

### 4. Verify

Before finalizing, check:

- Current-state claims are cited or clearly marked as assumptions.
- Scope says what changes and what deliberately does not.
- The plan follows cited existing patterns or explains the exception.
- Failure modes are covered when the change can fail.
- Tests name files or locations, behavior to assert, exact commands, and expected passing result.
- Rollback is clear for non-trivial changes.
- Domain terms match `CONTEXT.md`, or the plan includes a glossary update.
- No filler or hedging language remains.

If a check fails, return to exploration or ask the narrow question that resolves it.

## Task Tiers

### Tiny

Use for a single-file, single-behavior change with no public API, schema, migration, auth, billing, concurrency, cross-service, or durable domain effect.

Final plan shape:

```markdown
# [Specific Plan Title]

## Goal
[One sentence.]

## Current State
[One to three cited sentences.]

## Change
[Exact behavior/code change.]

## Test/Verification
[Exact command and expected result.]

## Assumptions
[Low-impact assumptions, or N/A with reason.]
```

### Standard

Use for default feature work, bug fixes with unclear cause, refactors, and changes touching more than one layer.

Final plan shape:

```markdown
# [Specific Plan Title]

## Goal
## Success Criteria
## Current State
## Scope
## Approach
## Changes (Dependency Order)
## Tracer Bullet
## Failure Modes
## Test Strategy
## Rollback Plan
## Assumptions
## Doc Updates
```

Keep sections brief. Combine related bullets. Name files only where needed to remove ambiguity.

### High-Risk

Use when the plan touches persisted data, public contracts, security/auth, payments, external integrations, concurrency, migrations, overloaded domain terms, or hard-to-undo rollout behavior.

Use the Standard shape plus:

- Compatibility and migration notes.
- Explicit rollback for code, data, and external side effects.
- A short risk register with P0/P1/P2 tiers.
- Pre-mortem findings only for real risks, not every possible category.

Do not present a High-risk plan with unresolved P0 risks.

## Domain Docs

Check existing domain docs before planning when the request introduces or reuses business language.

`CONTEXT.md`:

- Use it only as a glossary.
- Add or update a term when the session resolves canonical language, rejects a synonym, or fixes an overloaded concept.
- Do not put APIs, file paths, implementation details, acceptance criteria, or planning notes in it.

ADR:

- Recommend or add an ADR only when the decision is hard to reverse, surprising without context, and the result of a real tradeoff.
- Skip ADRs for obvious, local, mechanical, or easy-to-reverse choices.

## Quality Bar

A good plan lets implementation start immediately.

It states:

- What outcome is required.
- What the code does today.
- What changes, in dependency order.
- What stays out of scope and why.
- Which existing pattern to follow.
- How errors and edge cases behave.
- How to test the change and know it passed.
- How to roll back or why rollback is trivial.
- What assumptions remain and why they are low-impact.

If a plan would force the implementer to decide product behavior, architecture, interface shape, migration policy, or test strategy, it is not done.
