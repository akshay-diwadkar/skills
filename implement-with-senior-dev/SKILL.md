---
name: implement-with-senior-dev
description: Safely implement an approved, specific code-change plan as a minimal patch. Use when the user provides or points to an approved plan and wants Codex to implement it without scope expansion, preserve existing patterns, run focused verification, and report exactly what changed.
---

# Implement With Senior Dev

Implement only the approved plan in front of you. Treat the plan as a contract, not a suggestion queue. Every line of code you write must trace to a plan requirement. Every pattern you use must come from the repository, not from preference.

## Read Before Acting

- Read `references/implementation-protocols.md` before starting any gate work.
- Read `references/code-quality-checklist.md` before writing any code.
- Consult `references/implementation-hazards.md` when you encounter a problem during implementation.

## Contract

Always:

- Read the plan first and identify the plan source before editing.
- Refuse vague plans instead of inventing missing behavior.
- Preserve existing patterns, naming, architecture, error handling, and test style.
- Make the smallest patch that satisfies the plan.
- Implement every branch the plan specifies — including error, else, and default paths.
- Run focused verification that proves the planned behavior.
- Report exactly what changed, what ran, and what remains.

Never:

- Expand scope beyond the plan.
- Silently improve unrelated files, style, naming, tests, docs, or architecture.
- Rewrite broad areas when a local edit satisfies the plan.
- Overwrite user changes or clean a dirty worktree unless explicitly asked.
- Continue implementation after discovering a material contradiction between the plan and repo reality.
- Introduce new patterns, abstractions, or dependencies not specified in the plan.
- Improvise fixes when a CH-n cannot be applied as written.

## Gates

### 1. Plan Intake

Read the plan completely. Do not edit any files during this gate.

**Extract the plan structure:**

- **Detect the tier.** Tiny plans have no IDs — just Outcome, Evidence, Change, Verification sections. Standard plans use `SC-n`, `CH-n`, `T-n`, `C-n`, `R-n` IDs with a traceability matrix. High-Risk plans add Compatibility, Migration, and Durable Rollback sections.
- **Extract all plan IDs.** List every `SC-n` (success criterion), `CH-n` (implementation change), `T-n` (test case), `C-n` (constraint), and `R-n` (risk) with their definitions.
- **Build the CH-n dependency graph.** For each CH-n, identify the file and symbol it targets. Determine which CH-n items depend on symbols introduced by other CH-n items. Order: contracts and types first, core logic next, callers and orchestration after, tests last.
- **Extract the verification matrix.** Map each SC-n to its implementing CH-n and verifying T-n. Identify gaps — an SC-n without a T-n means verification is incomplete.
- **Extract constraints and risks.** Record each C-n and R-n with severity. P0/P1 risks must have mitigations that map to CH-n or T-n.
- **Identify verification commands.** Record every command the plan says to run, with expected results.

Follow the Plan Parsing Protocol in `references/implementation-protocols.md`.

**Completion criterion:** a dependency-ordered CH list exists, the verification matrix is complete, all IDs are accounted for, and the plan is specific enough to execute mechanically. If any of these fail, refuse under Vague Plan Refusal.

### 2. Workspace Reconnaissance

Inspect the repository before editing. Do not edit any files during this gate.

**Mandatory inspection sequence:**

a. **Check worktree cleanliness.** Run `git status` (or equivalent) for files targeted by the plan. If plan-targeted files have uncommitted changes, stop and report — do not overwrite user work.

b. **Read every file named in a CH-n.** Open each file, read the current state of the symbol being changed. Verify that the plan's `file:line` citations match reality. Record discrepancies.

c. **Build the pattern inventory.** For each file you will edit, record:
   - Naming convention (camelCase, snake_case, PascalCase)
   - Import organization (stdlib → third-party → local, alphabetical, grouped)
   - Error handling pattern (exceptions, return codes, Result types, error callbacks)
   - Logging pattern (structured, printf, framework-specific)
   - Comment and docstring style
   - String quote style (single, double, backtick)

d. **Find analogues.** For each CH-n, grep for similar operations in the same module. Record how the analogue handles the same concerns — this is the pattern you will follow.

e. **Read existing tests.** Open test files for affected modules. Record:
   - Test naming convention (test_verb_noun, should_verb_when, describe/it blocks)
   - Fixture style (factories, builders, raw data, conftest/beforeEach)
   - Assertion library and style
   - Test organization (flat functions, class-based, describe blocks)

f. **Verify dependencies.** Confirm that imports, packages, and config keys referenced by CH-n items exist in the workspace.

Follow the Pattern Matching Protocol in `references/implementation-protocols.md`.

**Completion criterion:** you know which local patterns to follow in every file you will edit, plan citations are verified against repo reality, and the workspace is clean for plan-targeted files. If material contradictions are found, consult `references/implementation-hazards.md` for recovery.

### 3. Dependency-Ordered Implementation

Apply code changes in dependency order, one CH-n at a time. This is the core implementation gate.

**For each CH-n, in dependency order:**

a. **Read the specification.** Re-read the CH-n completely: target file, target symbol, exact change, pseudocode (if any), branches, error paths, side effects, constraints.

b. **Open the target file.** Read the current state of the symbol being changed. Confirm it still matches your Gate 2 snapshot.

c. **Apply the change.** Translate the plan specification into code:
   - Use the pattern inventory from Gate 2 — match naming, style, error handling, imports.
   - Implement ALL branches from the pseudocode, including else/default/error paths. If the plan specifies a branch, it must appear in code.
   - For new symbols: find the right insertion point (after related symbols, respecting the file's organization).
   - For modified symbols: change only what the plan specifies. Preserve everything else.
   - For interface changes: match the plan's exact signature (parameters, types, defaults, return type).

d. **Update callers.** If this CH-n changes an interface, update every caller listed in the plan's propagation map. Follow the same local patterns.

e. **Smoke check.** After each CH-n, verify the file is syntactically valid. Run the narrowest available check (type checker, linter, or a single test covering this symbol) when practical.

f. **Run the code quality checklist** from `references/code-quality-checklist.md` against every file you edited in this CH-n.

Follow the Change Application Protocol in `references/implementation-protocols.md`.

**Completion criterion:** every CH-n is applied in dependency order, every edit traces to a plan requirement, local patterns are followed, all plan-specified branches exist in code, and no unrelated changes are included.

### 4. Test Implementation

Implement tests after code changes. This gate handles all T-n items.

**For each T-n:**

a. **Read the specification.** Re-read the T-n: exact input, exact expected output, setup requirements, the SC-n it verifies, the CH-n it covers.

b. **Identify the test file.** Use the plan's guidance. If it doesn't specify, find the existing test file for the module. If none exists, create one following the nearest analogue's test file structure.

c. **Build the fixture.** Use the minimum data needed to exercise the test. Follow local fixture patterns from the pattern inventory. Reuse existing fixtures when they match the needed shape.

d. **Write the test.**
   - Name describes the behavior being tested, not the function name.
   - Use the exact input from the T-n specification.
   - Assert the exact expected output from the T-n specification.
   - For error tests: assert the specific error type and message, not just "throws."

e. **Run the test in isolation.** Verify it passes. If it fails, the implementation (Gate 3) has a bug — trace back to the owning CH-n and fix before continuing.

Follow the Test Translation Protocol in `references/implementation-protocols.md`.

**Completion criterion:** every T-n has a corresponding test, each test passes in isolation, tests use exact inputs and outputs from the plan, and test patterns match the repository's existing style.

### 5. Verification

Run layered verification after all changes and tests are in place.

**Verification layers (run in order):**

1. **T-n tests.** Run all tests specified in the plan. Record pass/fail for each T-n.
2. **Module regression.** Run the full test suite for affected modules. Record results.
3. **Type and lint checks.** Run the project's type checker and linter if configured. These catch propagation errors that tests miss.
4. **Plan-specified commands.** Run every verification command from the plan's Verification section. Compare actual results to expected results.

**Failure triage:**

- **T-n test fails:** Compare the assertion to the plan's T-n specification. If the test matches T-n, the implementation has a bug — trace to the owning CH-n and fix. If the test doesn't match T-n, the test has a bug — fix the test.
- **Regression test fails:** Determine if the failure is caused by your changes or pre-existing. If pre-existing, record it. If caused by your changes, trace to the CH-n that broke it and fix.
- **Type/lint errors in files you edited:** Fix them — they indicate implementation bugs.
- **Type/lint errors in files you did NOT edit:** This is a propagation error. Check the plan's propagation map. If the file was listed, apply the minimal mechanical fix and note it. If not listed, consult `references/implementation-hazards.md`.

Follow the Verification Protocol in `references/implementation-protocols.md`.

**Completion criterion:** all T-n tests pass, no regressions in touched modules caused by plan changes, no new type/lint errors in changed files, and plan-specified verification commands produce expected results. Verification either passes, fails with concrete output, or is explicitly skipped with the blocking reason.

### 6. Post-Implementation Audit

Cross-check the implementation against the plan before reporting. Do not edit code during this gate unless the audit reveals a clear omission.

**Audit checks:**

a. **Traceability.** Walk the plan's traceability matrix. For each SC-n → CH-n → T-n mapping, verify:
   - The CH-n code change exists and matches the specification.
   - The T-n test exists and covers the CH-n.
   - The SC-n success criterion is satisfied by the combination.

b. **Scope discipline.** Review every file you edited. For each changed line, identify the CH-n it belongs to. Flag any line that cannot be traced to a CH-n — it is either a scope expansion (remove it) or a necessary mechanical propagation (record it in the report).

c. **Error path audit.** For every error/else/default branch in the plan's pseudocode, verify that the corresponding code path exists in the implementation.

d. **Constraint verification.** For each C-n marked "at-risk" in the plan, verify the constraint is still satisfied after implementation.

e. **Risk mitigation verification.** For each R-n with P0/P1 severity, verify the mitigation described in the plan is present in the code.

f. **Orphan check.** Verify no orphaned symbols exist — new types, functions, or imports that were added but never used because a dependent CH-n wasn't fully implemented.

**Completion criterion:** every plan requirement maps to implemented code, no scope expansion exists, all error paths are present, constraints are verified, and no orphaned symbols remain.

### 7. Report

Produce the final implementation report.

**Report shape:**

```markdown
## Implementation Report

**Plan source:** [path or description of the approved plan]
**Plan tier:** [Tiny / Standard / High-Risk]

### Changes
| CH | File | Symbol | What changed |
|---|---|---|---|
| CH-1 | `path/to/file` | `symbol_name` | [planned reason] |

### Unplanned Changes
- [file:line]: [mechanical propagation reason and justifying CH-n, or "None"]

### Verification Results
| Check | Result | Notes |
|---|---|---|
| T-1 | ✅ Pass | [test name] |
| Module regression | ✅ Pass | `[command]` |
| Type check | ✅ Pass | `[command]` |

### Skipped Checks
- [check]: [reason it was skipped]

### Residual Risks
- [risk description, or "None"]

### Follow-up
- [only exact required follow-up, or "None"]
```

For Tiny plans, use a simplified shape:

```markdown
## Implementation Report

**Plan source:** [source]

**Changed:** [file]: [reason]

**Verified:** [command]: [result]

**Follow-up:** [follow-up or "None"]
```

**Completion criterion:** the report names the plan source, every changed file with its CH-n, every test run with results, every skipped check with its reason, unplanned changes with justification, and any follow-up needed.

## Vague Plan Refusal

Refuse implementation when the plan lacks ANY of these:

- **Concrete goal** — what observable outcome the implementation achieves.
- **Success criteria** — measurable conditions that prove the goal is met.
- **Scope boundary** — what is in scope and what is explicitly out of scope.
- **Target behavior** — exact interfaces, logic, or changes to make (for Standard/High-Risk: CH-n items with specific files and symbols).
- **Verification path** — how to prove the implementation works (for Standard/High-Risk: T-n items with exact inputs and outputs).

**Detection heuristics for vague plans:**

- Plan says "update relevant files" without naming them.
- Plan says "handle errors appropriately" without specifying which errors.
- Plan says "add tests" without specifying what to test.
- Plan uses "as needed," "where appropriate," "if applicable," or "TBD."
- Plan's pseudocode has branches without else/default cases.
- Plan references functions or files without `file:line` citations (Standard/High-Risk only).

When refusing, state the specific missing items and recommend `plan-with-senior-dev` to turn the request into an executable plan. Do not make exploratory edits while trying to clarify a vague plan.

## Implementation Discipline

- Prefer local patterns over new abstractions.
- Add an abstraction only when the plan requires it or the repo already has the pattern for the same problem.
- Keep tests proportional to the patch risk and focused on the changed behavior.
- Treat generated files, lockfiles, migrations, public APIs, and snapshots as in scope only when the plan names them or the implementation cannot work without them.
- Stop and ask the user when the plan conflicts with repo facts, requires a missing secret or external system, or would force destructive git or filesystem operations.

## Implementation Hazards

Consult `references/implementation-hazards.md` when you encounter any of these during implementation:

- A CH-n cannot be applied because the target code doesn't match the plan.
- Existing tests fail after your changes in unexpected ways.
- Generated artifacts need updating but the plan doesn't mention them.
- The workspace has uncommitted user changes in plan-targeted files.
- Build or type errors appear in files you didn't edit.
- A dependency or secret referenced by the plan doesn't exist.
- The CH-n dependency graph has a cycle.
- Verification commands take unexpectedly long or fail with resource errors.

The hazards reference provides detection, recovery, and prevention guidance for each situation.

## Handoff Guidance

- Use `plan-with-senior-dev` to turn a vague request into a decision-complete, implementable plan.
- Use `optimize-codebase-with-senior-dev` when the goal is performance or capability optimization rather than implementing a specific plan.
- Use `codebase-issue-auditor` when the goal is to discover and prove bugs or risks rather than implement a known change.
