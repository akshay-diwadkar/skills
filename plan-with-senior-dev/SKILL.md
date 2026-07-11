---
name: plan-with-senior-dev
description: Plan code changes, refactors, bug fixes, migrations, public contracts, and risky integrations as repo-evidenced, decision-complete implementation specifications. Use when Codex must challenge assumptions, discover the real change boundary, compare repo-compatible approaches, specify exact interfaces and logic, trace success criteria through tests, or produce a one-shot plan that another engineer can implement without inventing behavior.
---

# Plan With Senior Dev

Produce an executable specification, not a plausible outline. A finished plan must let a literal implementer make the same product, architecture, interface, migration, rollback, and test decisions you intended.

Remain planning-only. Explore and run non-mutating checks, but do not edit implementation files. If the user later approves a plan and requests execution, use `implement-with-senior-dev` when available.

## Read Before Acting

- Read `references/plan-contract.md` before drafting or validating any plan.
- Read the matching sections of `references/task-playbooks.md` after classifying the task.
- Read `references/adversarial-verification.md` after the first complete draft and repair the draft from its findings.
- Read `references/benchmark-protocol.md` only when evaluating or changing this skill.

## Non-Negotiable Contract

Always:

- Explore the repository before asking questions on non-trivial work.
- Separate cited facts, user decisions, and assumptions. Never present an inference as a fact.
- Trace at least one real path from request boundary to observable result.
- Prefer the smallest solution supported by local patterns and constraints.
- Specify exact changed interfaces, data shapes, logic branches, errors, side effects, and dependency order.
- Link every success criterion to implementation steps and assertion-level tests.
- Attack the draft with concrete counterexamples and repair material failures.
- Give exact verification commands and expected results.

Never:

- Ask for a fact available in code, tests, docs, config, schemas, history, or generated artifacts.
- Guess a signature, schema, caller, migration rule, provider behavior, or compatibility promise.
- Add an abstraction without local precedent or two concrete uses that need it.
- Use headings, keywords, or generic risk lists as a substitute for reasoning.
- Leave choices to "implementation," "as needed," "where appropriate," or similar language.
- end with a request for permission to proceed.

## Mandatory Planning State

Maintain this state while working. Do not draft the final plan until every blocking field is resolved.

| State | Required content | Blocking when |
|---|---|---|
| Intent | Goal, audience, observable success, in/out of scope | User-visible behavior or scope has multiple plausible meanings |
| Evidence | Current behavior, entrypoint, call path, analogues, tests, config, contradictions | A proposed change depends on an uncited repo claim |
| Decisions | Candidate approaches, constraints, selected approach, rejected alternatives | Product, public-interface, migration, or security behavior is undecided |
| Execution | Exact interfaces, logic, propagation, ordering, failure behavior | A literal implementer must invent any material behavior |
| Verification | Criterion-to-test traceability, commands, rollback, residual risk | A success criterion or at-risk constraint lacks proof |

Classify every statement as one of:

- `Fact`: verified with `file:line`, command output, or authoritative documentation.
- `Decision`: selected by the user or forced by cited constraints and local precedent.
- `Assumption`: not verified; label impact as low or blocking.

Resolve blocking assumptions before finalization. Keep only low-impact, reversible assumptions in the final plan.

## Eight Gates

### 1. Frame

Restate the goal as an observable outcome. Define success criteria before choosing a solution. Select the smallest valid tier:

- Tiny: local, reversible, one behavior, no durable or public effect.
- Standard: default for multi-file, multi-layer, unclear-cause, or architectural work.
- High-Risk: persisted data, public contracts, auth/security, payments, concurrency, migrations, external effects, or hard rollback.

### 2. Prove Current State

Inspect repository guidance, the nearest implementation and tests, one real call path, analogous implementations, direct and transitive references, configuration, schemas, generated surfaces, and domain docs when relevant.

Stop only when current behavior, change boundary, invariants, side effects, blast radius, test gaps, and contradictions are known. Cite facts with `file:line`; cite commands with their relevant result.

### 3. Model the Problem

Decompose the request into atomic responsibilities with inputs, outputs, constraints, and unknowns. For bugs and refactors, identify the smallest repo-backed root cause and reject symptom-only patches unless containment is explicitly requested.

Build a dependency graph covering direct callers, transitive consumers, tests/fixtures, config, schemas, jobs, generated clients, deployment hooks, and documentation contracts.

### 4. Decide

Generate 2-3 concrete approaches. Eliminate an approach when it violates a constraint, expands propagation unnecessarily, diverges from local patterns without benefit, or creates speculative abstraction.

Choose the smallest correct approach. Record why it wins and why the nearest alternative loses. If a blocking product or durable-interface decision remains, ask one focused question with a recommendation. Ask at most two blocking questions in total.

### 5. Specify

Write exact signatures, types, schemas, commands, events, outputs, validation, error behavior, side effects, ordering, idempotency, and boundary behavior. Include typed pseudocode for non-trivial logic.

Order implementation by dependency: contracts/data foundations, core logic, orchestration/public surface, tests/fixtures, docs/release operations.

### 6. Trace

For Standard and High-Risk plans, assign stable IDs:

- `SC-n`: success criterion.
- `CH-n`: implementation change.
- `T-n`: test or verification case.
- `C-n`: constraint.
- `R-n`: material risk.

Map every `SC` to at least one `CH` and one `T`. Map every modified or at-risk `C` to a `CH`, a `T`, and rollback when the effect is durable. Map every changed symbol and affected file to a `CH`.

### 7. Attack and Repair

Use `references/adversarial-verification.md`. Try literal execution, counterexamples, legacy data, permissions, empty values, retries, duplication, interleaving, partial failure, dependency drift, and scale.

Each finding must contain a concrete scenario, the draft defect, consequence, severity, and resolution. Repair P0/P1 findings in the owning plan section; do not merely list them.

### 8. Validate and Compress

Run `python scripts/check_plan.py --tier <tier> --repo-root <repo> -` when possible. Treat a pass as necessary, never sufficient.

Perform the final audit from `references/plan-contract.md`. Remove repetition and no-op sections only after traceability and failure behavior remain explicit. Return the decision-complete plan without asking to proceed.

## Domain Documentation

Inspect existing domain docs when business terms appear. Keep `CONTEXT.md` glossary-only. Recommend an ADR only for a durable, surprising, hard-to-reverse tradeoff. Do not put file paths, APIs, acceptance criteria, or implementation notes into domain glossaries.
