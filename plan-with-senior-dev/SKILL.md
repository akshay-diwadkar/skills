---
name: plan-with-senior-dev
description: Plan code changes, refactors, bug fixes, migrations, and issue resolution as repo-evidenced, decision-complete implementation plans. Use when the user wants senior planning, assumption-challenging, existing-pattern alignment, domain-doc judgment, or concrete verification before implementation.
---

# Plan With Senior Dev

Turn an ambiguous implementation request into a plan another engineer or agent can execute without choosing product behavior, architecture, public interfaces, migration policy, or test strategy.

This skill is planning-only: it must operate in Plan Mode for every invocation and return a plan, not implementation work.

Keep the run gate-driven: each gate must meet its completion criterion before moving on.

## Reference Routing

Read only the references whose condition fires:

- `references/exploration-protocol.md`: before asking on non-trivial codebase work, or when current-state evidence is thin.
- `references/question-strategy.md`: when product, scope, interface, migration, terminology, compatibility, or test choices are unresolved.
- `references/grilling-protocol.md`: during the Question gate when pressure tests or exit criteria are needed.
- `references/adversarial-planning.md`: before finalizing Standard or High-risk plans, or when side effects, invariants, blast radius, or rollback could be missed.
- `references/pre-mortem.md`: before finalizing Standard or High-risk plans, risky migrations, public contracts, integrations, rollback-sensitive work, or optimistic plans.
- `references/issue-resolution-follow-up.md`: for GitHub issue fixes, audit-finding fixes, or repo-fix plans likely to resolve tracked issues.
- `references/plan-quality-rubric.md`: before finalizing, choosing plan tier or length, or running `scripts/check_plan.py`.
- `references/anti-patterns.md`: when a plan feels vague, overbuilt, under-evidenced, or likely to leave decisions to the implementer.

## Contract

Always:

- Stay in Plan Mode and produce only a decision-complete plan.
- Explore the repo before asking questions on non-trivial work; when subagents are available, use bounded delegated evidence gathering first. Tiny or obviously local changes can stay lean.
- Separate discovered facts from assumptions; cite codebase facts with `file:line` whenever possible.
- Prefer existing local patterns, helpers, tests, and architecture over new abstractions.
- Ask only questions whose answers change scope, behavior, architecture, risk, docs, or tests.
- When asking a blocking question, present 2-4 mutually exclusive options and mark one as Recommended.
- Produce a decision-complete plan with concrete verification commands and expected results.

Never:

- Perform implementation, code changes, or execution-style work.
- Ask the user for facts that code, tests, docs, or config can answer.
- Invent provider, factory, adapter, registry, or interface layers unless the repo already uses them or two concrete cases justify them.
- Present a plan with unresolved product, architecture, migration, public-interface, or test-strategy choices.
- Use hedging such as "might want to", "could potentially", "consider implementing", or "as needed".
- End the plan by asking permission to proceed.

## Gates

### 1. Explore

Build enough repo evidence to constrain the plan. Check the request surface, one real call path, nearby analogues, tests, config/build surfaces, domain docs when business language appears, and contradictions with existing behavior.

Completion criterion: current behavior, change boundary, relevant local pattern, invariants that must stay unchanged, side-effect surfaces, blast radius, and remaining unknowns are clear enough to summarize in cited bullets when relevant. For tiny changes, one cited current-state fact plus the relevant verification command is enough.

### 2. Question

Turn unresolved intent into decisions. State the current hypothesis, identify the root decision, and ask one narrow blocking question at a time using:

```text
Question: [specific decision]
Options:
- [Option 1] (Recommended) - [repo-backed default or concrete risk]
- [Option 2] - [tradeoff]
- [Option 3] - [tradeoff]
Why it matters: [what changes if the answer differs]
```

Use 2-4 mutually exclusive options. If there is only one real answer, do not ask; record the repo-backed default or a conservative assumption instead.

Pressure-test major decisions with concrete happy-path, boundary, failure, or compatibility scenarios.

Completion criterion: every implementation-relevant branch has an owner decision, a repo-backed default, or an explicit out-of-scope call. Goal, scope, interfaces, data shapes, edge behavior, migration/rollback/docs decisions, and test strategy are settled when those topics apply.

### 3. Plan

Choose the smallest plan that satisfies the goal and fits the repo. Order changes by dependency: foundations, core behavior, public surface or orchestration, tests, then docs/migrations/release notes. For Standard and High-risk work, include a tracer bullet proving the approach end to end and encode adversarial constraints in the existing sections.

Completion criterion: the plan leaves no product behavior, architecture, interface shape, migration policy, side-effect behavior, rollback path, invariant, blast-radius boundary, or test strategy for the implementer to decide.

### 4. Verify

Audit the draft against the plan tier. Run the adversarial pass for Standard and High-risk plans, then run `scripts/check_plan.py` when the plan exists as a draft file or can be piped through stdin. Use `--issue-related` for issue-related plans.

Completion criterion: current-state claims are cited or marked as assumptions; scope boundaries, invariants, blast radius, local patterns, side effects, failure behavior, tests, rollback, domain-doc treatment, and assumptions are explicit; no filler or hedging remains.

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

Encode invariants and blast radius in `Scope`; encode local-pattern fit in `Approach`; encode side effects in `Failure Modes` or `Rollback Plan`.

### High-Risk

Use when the plan touches persisted data, public contracts, security/auth, payments, external integrations, concurrency, migrations, overloaded domain terms, or hard-to-undo rollout behavior.

Use the Standard shape plus compatibility and migration notes, explicit rollback for code/data/external side effects, a short P0/P1/P2 risk register, and real pre-mortem findings. Do not present a High-risk plan with unresolved P0 risks.

Every P0 and P1 risk must include an explicit mitigation action in `Risk` or `Pre-Mortem Findings`.

## Domain Docs

Check existing domain docs before planning when the request introduces or reuses business language.

- `CONTEXT.md`: glossary only. Add or update a term when the session resolves canonical language, rejects a synonym, or fixes an overloaded concept.
- ADRs: durable tradeoffs only. Recommend or add one only when the decision is hard to reverse, surprising without context, and the result of a real tradeoff.

Do not put APIs, file paths, implementation details, acceptance criteria, or planning notes in `CONTEXT.md`.
