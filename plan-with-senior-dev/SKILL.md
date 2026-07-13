---
name: plan-with-senior-dev
description: Plan code changes, refactors, bug fixes, migrations, public contracts, and risky integrations as repo-evidenced, decision-complete implementation specifications. Use when Codex must challenge assumptions, discover the real change boundary, compare repo-compatible approaches, specify exact interfaces and logic, trace success criteria through tests, or produce a one-shot plan that another engineer can implement without inventing behavior.
---

# Plan With Senior Dev

Produce an executable specification, not a plausible outline. A finished plan must let a literal implementer make the same product, architecture, interface, migration, rollback, and test decisions you intended — without guessing, without backtracking, and without asking follow-up questions.

Remain planning-only. Explore and run non-mutating checks, but do not edit implementation files. If the user later approves a plan and requests execution, use `implement-with-senior-dev` when available.

## Read Before Acting

- Read `references/cognitive-protocols.md` before starting any gate work.
- Read `references/plan-contract.md` before drafting or validating any plan.
- Read the matching sections of `references/task-playbooks.md` after classifying the task.
- Read `references/worked-examples.md` for the matching tier before writing the first draft.
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
- End with a request for permission to proceed.

## Decision Resolution Protocol

Before asking the user a question:

1. Search the codebase for the answer (grep, read tests, check config).
2. Check if local precedent resolves the ambiguity (how does the nearest analogue handle it?).
3. Check if a constraint forces exactly one answer (backward compatibility, existing schema, security policy).

Ask only when ALL of these are true:

- Two valid approaches exist.
- The choice affects user-visible behavior or a public/shared interface.
- No repo evidence distinguishes them.

When asking (at most two blocking questions total):

- State the two concrete options with their tradeoffs.
- Recommend one with the cited reason.
- Explain what changes in the plan if they pick the other.

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

## Planning Gates

### Gate 0: Orient

Before any detailed work, classify the task and commit to a tier.

1. **Classify the task type.** Read the matching section of `references/task-playbooks.md`:
   Feature, Bug Fix, Refactor, Public Contract, Security, Concurrency, External Integration.
   Apply multiple sections when the change crosses categories.

2. **Estimate blast radius.** Before reading any code, estimate: how many files, layers, and consumers are likely affected? This is a rough estimate to guide exploration depth.

3. **Select the tier.** Choose the smallest valid tier:
   - **Tiny**: local, reversible, one behavior, no durable or public effect.
   - **Standard**: default for multi-file, multi-layer, unclear-cause, or architectural work.
   - **High-Risk**: persisted data, public contracts, auth/security, payments, concurrency, migrations, external effects, or hard rollback.

4. **Commit.** State the task type, tier, and rough blast radius. If uncertain between two tiers, choose the higher one.

❌ Anti-patterns:
- Defaulting to Standard for everything without considering if Tiny fits.
- Choosing Tiny for something that touches a shared interface.
- Skipping orientation and diving straight into code reading.

### Gate 1: Frame

Restate the goal as an observable outcome. Define success criteria before choosing a solution.

Before writing this section, answer internally:
- What is the ONE observable thing that will be different when this plan is implemented?
- Who will observe it (user, developer, automated test, monitoring)?
- What does "done" look like in terms of exact behavior, not in terms of code changes?

Produce:
- Observable outcome (not "refactor X" but "X now does Y instead of Z").
- Success criteria with measurable verbs (returns, rejects, displays, emits — not "works correctly").
- Explicit in-scope and out-of-scope boundaries.
- What must NOT change (invariants).

❌ Anti-patterns:
- Success criteria that use "works," "functions correctly," or "is improved."
- Scope that says "update relevant files" without naming them.
- Missing invariants (what stays the same is as important as what changes).

### Gate 2: Prove Current State

Follow the Evidence Gathering Protocol from `references/cognitive-protocols.md`. Do not draft until every applicable step completes.

**Mandatory search sequence:**

a. Find the entry point: grep for the function/class/route named in the request.
b. Read the file. Record: file path, line number, signature, return type, error paths.
c. Trace ONE real call path: caller → entry → dependency → side effect → output.
   For each hop, record: `file:line`, what it passes, what it receives.
d. Search for analogues: grep for similar operations in the same module/package.
   Record: how the analogue handles the same concern (error, validation, auth).
e. Find tests: grep for the function name in test files.
   Record: what's tested, what's not, fixture setup.
f. Check config/schema: search for any config keys, env vars, schema definitions
   referenced by the call path.
g. Synthesize contradictions: compare what the code does vs. what docs/comments say.
   Record each contradiction with `file:line` for both sides.

**Stop when:** current behavior, change boundary, invariants, side effects, blast radius, test gaps, and contradictions are all known and cited with `file:line`.

❌ Anti-patterns:
- Citing a file without a line number.
- Saying "the function handles errors" without naming which errors and where.
- Describing behavior from memory instead of from code inspection.
- Using "should" or "would" for current state (use "does" — you read the code).
- Reading only the entry point file without tracing callers or dependencies.

### Gate 3: Model the Problem

Decompose the request into atomic responsibilities with inputs, outputs, constraints, and unknowns. For bugs and refactors, follow the Root Cause Analysis Protocol from `references/cognitive-protocols.md`.

Before writing this section, answer internally:
- What is the simplest possible change that would satisfy the success criteria?
- What makes this harder than it appears? (Hidden callers, shared state, implicit contracts)
- Is there a local analogue that already solves a similar problem? What pattern does it use?

Produce:
- Atomic responsibilities with clear inputs and outputs.
- For bugs: root cause identification with evidence trail (not symptom location).
- Dependency graph covering direct callers, transitive consumers, tests/fixtures, config, schemas, jobs, generated clients, deployment hooks, and documentation contracts.

❌ Anti-patterns:
- Patching the symptom location for a bug without tracing the root cause.
- Skipping the analogue search (the codebase often already has the pattern you need).
- Building a dependency graph from memory instead of from grep results.

### Gate 4: Decide

Generate 2-3 concrete approaches. Choose the smallest correct one.

Before writing this section, answer internally:
- For each approach: what is the ONE strongest argument for it? Against it?
- Which approach requires the fewest file changes?
- Which approach follows existing patterns in this codebase?

For each approach, state:
- The exact change it requires (files, functions, lines).
- Which constraints it satisfies and which it strains.
- Why it wins or loses against the others.

Apply the Decision Resolution Protocol. If a blocking product or durable-interface decision remains after searching the codebase and checking precedent, ask one focused question with a recommendation.

Record:
- Selected approach with the reason (citing constraint or precedent).
- Rejected alternatives with specific drawbacks (not "more complex" — how specifically).

❌ Anti-patterns:
- Presenting only one approach (always consider at least one alternative).
- Rejecting an alternative with a vague reason like "too complex" without specifics.
- Choosing an approach that introduces a new pattern when an existing pattern works.

### Gate 5: Specify and Trace

Write exact specifications AND build traceability simultaneously. Do not generate IDs post-hoc.

**Specification requirements:**
- Exact signatures, types, schemas, commands, events, outputs.
- Validation rules, error behavior, side effects, ordering, idempotency.
- Typed pseudocode for non-trivial logic (with all branches, including error/else/default).
- Boundary behavior for every new input (null, empty, zero, max).

**Order implementation by dependency:**
1. Contracts and data foundations
2. Core logic
3. Orchestration and public surface
4. Tests and fixtures
5. Docs and release operations

**Build traceability inline — assign IDs as you specify, not after:**

For Standard and High-Risk plans, assign stable IDs:
- `SC-n`: success criterion.
- `CH-n`: implementation change (must name a specific file and symbol).
- `T-n`: test or verification case (must name exact input and exact output).
- `C-n`: constraint.
- `R-n`: material risk.

Map every `SC` to at least one `CH` and one `T`. Map every modified or at-risk `C` to a `CH`, a `T`, and rollback when the effect is durable. Map every changed symbol and affected file to a `CH`.

**For interface changes:** Follow the Interface Change Protocol from `references/cognitive-protocols.md`. Show complete before/after shapes in code blocks — never prose deltas.

❌ Anti-patterns:
- Pseudocode that omits the else/error/default branch.
- CH-n that says "update the service" instead of "update `service.py:load_report` to add tenant filter."
- T-n that says "test that it works" instead of "Given input X, assert output Y."
- Generating SC/CH/T IDs after writing the plan and retro-fitting them (build them as you go).
- Missing boundary behavior (what happens with null, empty, zero?).

### Gate 6: Attack and Repair

Follow `references/adversarial-verification.md`. This is NOT a cosmetic exercise — it is where most plan defects are caught.

**Step 1: Pre-Attack Reality Check.**
Before any attacks, re-verify every `file:line` citation, every signature, every "unchanged" claim. Fix discrepancies before proceeding.

**Step 2: Run Mandatory Attack Templates.**
Run every applicable template from `references/adversarial-verification.md`:
- A1: The Forgotten Caller
- A2: The Empty/Boundary Input
- A3: The Concurrent Request
- A4: The Rollback Scenario
- A5: The Scale Surprise
- A6: The Literal Implementation Test

**Step 3: Repair.**
Each P0/P1 finding must modify the owning plan section — do not merely list findings.

**Step 4: Cross-consistency audit.**
Compare success criteria with invariants. Compare pseudocode with test expectations. Compare propagation entries with implementation steps.

❌ Anti-patterns:
- Cosmetic findings: "Consider adding logging" is not an attack.
- Listing risks without modifying the plan to address them.
- Running one attack pass and declaring victory without checking repairs.
- Manufacturing three findings to seem thorough when no real issues exist (state "no material finding" with evidence instead).

### Gate 7: Validate and Compress

Run `python scripts/check_plan.py --tier <tier> --repo-root <repo> -` when possible. Treat a pass as necessary, never sufficient.

**Before Finalization Checklist** — if any answer is "no," return to the owning gate:

- [ ] Every `file:line` citation exists in the repo (verified by grep/read).
- [ ] Every function signature in the plan matches the actual code.
- [ ] Every "unchanged" claim is verified (no pending changes affect it).
- [ ] Every test case has an exact input AND exact expected output.
- [ ] Every CH-n names a specific file and symbol.
- [ ] No section contains "as needed," "where appropriate," or "if applicable."
- [ ] The plan can be implemented by reading it top-to-bottom without backtracking.
- [ ] Every P0 is resolved. Every P1 has changed the plan.
- [ ] Two literal implementers would produce the same code from this plan.

Perform the final audit from `references/plan-contract.md`. Remove repetition and no-op sections only after traceability and failure behavior remain explicit. Return the decision-complete plan without asking to proceed.

## Domain Documentation

Inspect existing domain docs when business terms appear. Keep `CONTEXT.md` glossary-only. Recommend an ADR only for a durable, surprising, hard-to-reverse tradeoff. Do not put file paths, APIs, acceptance criteria, or implementation notes into domain glossaries.
