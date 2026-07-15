# Implementation Protocols

Step-by-step execution procedures for each implementation gate activity. Follow these protocols literally during implementation. Each protocol specifies concrete actions, expected outputs, and stop conditions.

---

## Plan Parsing Protocol

### When to use
Gate 1 (Plan Intake) for every plan.

### Steps

1. **Identify the plan tier.** Read the plan structure and classify:
   - **Tiny**: No IDs. Contains only a Change section (possibly with a Goal and Verification). No SC-n, CH-n, T-n, C-n, or R-n identifiers.
   - **Standard**: Contains SC-n (success criteria), CH-n (changes), T-n (tests), and optionally C-n (constraints) and R-n (risks). Has a traceability matrix or verification mapping.
   - **High-Risk**: Everything in Standard, plus Compatibility Matrix, Migration Path, and/or Rollback sections.
   Record the tier. The tier determines the rigor of subsequent gates.

2. **Extract all plan IDs.** For each ID type present, build a registry:
   - `SC-n`: Read the success criterion text. Record what observable behavior or property it asserts.
   - `CH-n`: Read the file path, symbol name, change type (add/modify/delete), pseudocode, branches, error paths, and side effects. Record every field.
   - `T-n`: Read the exact input, exact expected output, and setup requirements. Record which SC-n and CH-n it covers (the plan states this explicitly).
   - `C-n`: Read the constraint text and its severity (hard constraint vs preference).
   - `R-n`: Read the risk description, likelihood, impact, and mitigation.
   For Tiny plans, there are no IDs to extract — proceed to step 4 with the Change section as a single implicit work unit.

3. **Build the CH-n dependency graph.** For each CH-n:
   a. Read the file and symbol it changes.
   b. Read the pseudocode. Identify which types, functions, constants, or interfaces it references.
   c. Check: are any of those referenced symbols introduced or modified by another CH-n? If yes, that CH-n is a dependency.
   d. Order the CH-n items by dependency depth. The standard ordering is:
      - Types, interfaces, contracts (depended on by everything)
      - Core logic (depends on types, depended on by callers)
      - Orchestration, callers, integration points (depend on core logic)
      - Tests (depend on all production code)
      - Documentation, configuration (depend on final interfaces)
   e. Record the ordered list: `[CH-1, CH-3, CH-2, CH-4, ...]` with the reason for each ordering decision.

4. **Extract the verification matrix.** Build a table mapping T-n to the SC-n and CH-n items it covers:
   ```
   T-n → SC-n covered → CH-n exercised
   T-1 → SC-1         → CH-1, CH-2
   T-2 → SC-2         → CH-3
   ```
   Check: is every SC-n covered by at least one T-n? If not, record the gap.
   Check: is every CH-n exercised by at least one T-n? If not, record the gap.
   For Tiny plans, the verification section substitutes for this matrix — record the verification commands and what they prove.

5. **Extract constraints and risks.** For each C-n:
   - Record the constraint and identify which CH-n items it affects.
   - Hard constraints must be checked during implementation. Preferences should be followed unless a local pattern conflicts.
   For each R-n:
   - Record the risk and its mitigation.
   - Identify which CH-n items are affected by the risk.
   - For High-Risk plans, cross-reference R-n items with the Compatibility/Migration/Rollback sections.

6. **Identify plan-specified verification commands.** Read the plan's Verification section. Record every command, script, or test invocation the plan specifies. These are mandatory — they must be run during Gate 5.

### Stop when
- The plan tier is identified
- A dependency-ordered CH list exists (or a single implicit work unit for Tiny plans)
- The verification matrix is complete with coverage gaps noted
- All IDs (SC-n, CH-n, T-n, C-n, R-n) are registered with their definitions
- Plan-specified verification commands are recorded

### Common failures
- **Ignoring dependency order**: Editing files in the order they appear in the plan rather than dependency order. Fix: Always build the dependency graph and implement types/contracts before their consumers.
- **Missing implicit dependencies**: CH-n that imports or calls a symbol from another CH-n without the plan explicitly stating the dependency. Fix: Read the pseudocode of every CH-n and check for cross-references.
- **Skipping the matrix for Tiny plans**: Tiny plans still need a mental mapping of what the verification commands prove. Fix: Even without IDs, confirm that the verification commands cover the stated goal.

---

## Pattern Matching Protocol

### When to use
Gate 2 (Workspace Reconnaissance) for every plan.

### Steps

1. **Read every file named in any CH-n.** For each file, open it and read it completely (or read enough to capture the file's conventions). Record:
   - **Naming style**: camelCase, snake_case, PascalCase, UPPER_SNAKE_CASE for constants. Note if the file mixes styles (some codebases use PascalCase for classes and camelCase for functions). Cite `file:line` examples.
   - **Import organization**: stdlib → third-party → local? Alphabetical within groups? Grouped by feature? Absolute vs relative imports? Cite the import block with `file:line`.
   - **Error handling pattern**: Exceptions (try/catch/throw)? Return codes? Result/Either types? Error-first callbacks? What error types are used (custom classes, built-in, string messages)? Cite `file:line`.
   - **Logging pattern**: Structured logging (key-value pairs)? Printf-style? Which logger/library? What log levels for what situations? Cite `file:line`.
   - **Comment and docstring style**: JSDoc? Google-style? NumPy-style? Inline comments? No comments? Cite `file:line`.
   - **Function organization**: Are functions ordered by visibility (public → private)? By call order? Alphabetically? Cite the function ordering with `file:line`.

2. **Find the nearest analogue.** For each CH-n, search the same module/package for a function or class that does a similar operation (e.g., another endpoint, another validator, another event handler, another model method).
   - Read how the analogue handles: input validation, authorization, the main operation, error paths, response formatting, logging, cleanup.
   - Record the analogue with `file:line` and note which patterns to replicate.
   - If no analogue exists in the same module, expand to the nearest related module. Record that the analogue is from a different module and note any convention differences.

3. **Read existing test files for affected modules.** For each module being modified, find and read its test file(s). Record:
   - **Test naming convention**: `test_<behavior>`, `it('should <behavior>')`, `<ClassName>_<method>_<scenario>`, or similar. Cite `file:line` examples.
   - **Fixture style**: Factory functions? Builder patterns? Raw inline data? Shared fixtures (conftest.py, beforeEach, setUp)? Cite `file:line`.
   - **Assertion library and style**: Built-in assert? expect().toBe()? assertThat()? Hamcrest matchers? Cite `file:line`.
   - **Test organization**: Flat functions? Nested describe/context blocks? Class-based? Cite `file:line`.
   - **Mock/stub patterns**: What gets mocked? How? (jest.mock, unittest.mock, sinon, manual stubs). Cite `file:line`.

4. **Build the pattern inventory.** Create a checklist summarizing every convention discovered:
   ```
   Pattern Inventory for [module/area]:
   - Naming: [style] — see [file:line]
   - Imports: [organization] — see [file:line]
   - Errors: [pattern] — see [file:line]
   - Logging: [pattern] — see [file:line]
   - Comments: [style] — see [file:line]
   - Tests: [naming] / [fixtures] / [assertions] — see [file:line]
   - Analogue: [function] in [file:line] — handles [concerns]
   ```
   This inventory is your reference during Gate 3 and Gate 4. Every implementation decision should match it.

### Stop when
- Every file named in a CH-n has been read and its conventions recorded
- A nearest analogue is identified for each CH-n with `file:line` citation
- Test conventions are recorded with `file:line` citations
- The pattern inventory is complete and covers: naming, imports, errors, logging, comments, tests, and analogues

### Common failures
- **Assuming conventions from memory**: Writing code in a style you've seen in other projects instead of reading the actual file. Fix: Always open the file and cite `file:line` for every convention claim.
- **Cross-module contamination**: Applying patterns from module A to module B when module B uses different conventions. Fix: Build a separate pattern inventory for each module if conventions differ.
- **Ignoring test patterns**: Writing tests in your preferred style instead of matching the existing test file. Fix: Always read the existing test file before writing new tests.
- **Skipping the analogue search**: Implementing from scratch when a similar operation already exists in the same module. Fix: Always grep for similar operations.

---

## Change Application Protocol

### When to use
Gate 3 (Implementation) for each CH-n item, processed in dependency order.

### Steps

1. **Read the CH-n specification completely.** Before writing any code, read and internalize:
   - Target file and symbol (function, class, method, constant, type)
   - Change type: add new symbol, modify existing symbol, or delete symbol
   - Pseudocode or specification for the change
   - All branches: happy path, error paths, else/default cases, edge cases
   - Side effects: DB writes, network calls, file mutations, cache updates, events emitted
   - Propagation requirements: callers that need updating, re-exports, generated code

2. **Open the target file and read the current state.** Read the file around the symbol being changed:
   - For modifications: read the full current implementation of the symbol. Note line numbers.
   - For additions: read the surrounding code to identify the insertion point.
   - For deletions: read all references to the symbol to confirm the plan accounts for them.

3. **Determine the insertion or edit point.**
   - **Adding a new symbol**: Find the right position in the file respecting the file's organizational pattern (from the pattern inventory). Place it after related symbols, not at the end of the file unless that matches the local pattern. If adding an import, place it in the correct import group.
   - **Modifying an existing symbol**: Identify the exact lines to change. Mentally mark the boundaries — everything outside these boundaries must be preserved exactly.
   - **Deleting a symbol**: Confirm the plan's propagation map accounts for all references. Remove the symbol and its associated imports/exports if they become unused.

4. **Translate pseudocode into real code.** Using the pattern inventory from Gate 2:
   - Match the local naming convention for all new identifiers.
   - Match the local error handling pattern. If the pseudocode says "throw error", use the local error type and pattern. If the module uses Result types, return a Result.
   - Match the local logging pattern. If the pseudocode says "log the operation", use the local logger and format.
   - Match the local import style when adding new imports.
   - **Implement ALL branches.** If the pseudocode specifies an error path, it must appear in the code. If the pseudocode specifies an else/default case, it must appear in the code. Do not skip branches because they seem unlikely.
   - **Respect constraints.** Check each C-n that applies to this CH-n and verify the code satisfies it.

5. **Handle interface changes.** If this CH-n changes a function signature, type, or API:
   - Verify the complete before/after shape matches the plan exactly.
   - Check the plan's propagation map for callers that need updating.
   - If caller updates are part of a different CH-n, do NOT update them now — they will be handled in dependency order.
   - If caller updates are part of THIS CH-n, update them now.

6. **Post-change file review.** After applying the change:
   - Read the modified file (or the relevant section) to verify it is syntactically correct.
   - Check that surrounding code is not broken (e.g., no dangling references, no mismatched brackets, no orphaned imports).
   - Verify that the change does not introduce patterns that conflict with the pattern inventory.

7. **Run a quick smoke check.** If the project supports it:
   - Run the type checker on the changed file (e.g., `tsc --noEmit`, `mypy`, `pyright`).
   - Run the linter on the changed file.
   - Run the narrowest test covering this specific symbol.
   Record the result. If the smoke check fails, fix the issue before proceeding to the next CH-n.

### Stop when
- The code change matches the CH-n specification exactly
- All plan-specified branches (happy path, error, else, default, edge cases) exist in the code
- Local patterns from the pattern inventory are followed
- The file reads correctly with no syntax or structural damage
- Smoke check passes (or is recorded as skipped with reason)

### Common failures
- **Happy-path-only implementation**: Writing the main logic and skipping the error/else/default branches from the pseudocode. Fix: Check every branch in the CH-n pseudocode against the implemented code before moving on.
- **Pattern divergence**: Introducing a new pattern (e.g., a new error type, a new logging format) when the file already has a local pattern for the same concern. Fix: Consult the pattern inventory before every implementation decision.
- **Forgotten caller updates**: Changing a function signature without updating the callers listed in the propagation map. Fix: After every signature change, immediately check the propagation map.
- **Scope creep during implementation**: Noticing an unrelated issue in the file and fixing it. Fix: If it's not in the plan, don't touch it. Record it as a follow-up item if it's important.
- **Out-of-order application**: Implementing CH-5 before CH-2 because CH-5 is in a file you already have open. Fix: Always follow the dependency order from Gate 1.

---

## Test Translation Protocol

### When to use
Gate 4 (Test Implementation) for each T-n item.

### Steps

1. **Read the T-n specification completely.** Extract:
   - **Exact input**: The precise values, objects, or payloads the test provides. Not "valid input" — the actual data.
   - **Exact expected output**: The precise return value, response body, state change, or side effect. Not "success" — the actual value.
   - **Setup requirements**: What state must exist before the test runs (database rows, files, mocks, config).
   - **SC-n coverage**: Which success criteria this test proves.
   - **CH-n coverage**: Which changes this test exercises.

2. **Identify the test file.** In order of preference:
   a. The plan explicitly names the test file → use it.
   b. An existing test file covers the module being tested → add the test there.
   c. No existing test file → create one following the nearest analogue's test file structure (from the pattern inventory). Match the directory structure, naming convention, and boilerplate.

3. **Build the fixture/setup.** Follow local fixture patterns from the pattern inventory:
   - **Reuse existing fixtures** when they provide the data needed for T-n. Do not create a new fixture that duplicates an existing one.
   - **Extend existing fixtures** if T-n needs a slight variation. Follow the local pattern for fixture customization (e.g., factory overrides, builder modifications).
   - **Create new fixtures** only when no existing fixture covers the setup. Follow the local fixture style (factories, builders, raw inline data, shared setup files).
   - Use the **minimum data** needed to exercise the test. Do not build elaborate setups when a simple one suffices.
   - If the test requires mocks/stubs, follow the local mocking pattern (from the pattern inventory).

4. **Write the test function.**
   - **Name**: Describe the behavior being tested, not the function being called. Follow the local naming convention (e.g., `test_returns_empty_list_when_no_items_exist`, `it('should return 404 when resource is missing')`).
   - **Arrange**: Set up the fixture and preconditions from step 3.
   - **Act**: Call the function/endpoint with the exact input from T-n.
   - **Assert**: Assert the exact expected output from T-n. Use the local assertion style (from the pattern inventory). Do NOT weaken the assertion — if T-n says the output is `[1, 2, 3]`, assert `[1, 2, 3]`, not `length == 3`.
   - **Cleanup**: If the test creates side effects (files, DB rows, external state), clean them up following the local pattern.

5. **Handle regression tests (bug fixes).** If T-n is a regression test for a bug fix:
   - Ideally, verify the test fails before the fix and passes after. If you can verify this easily (e.g., by temporarily reverting the fix), do so and record the result.
   - If you cannot easily verify the "before" state, note this in the implementation report: "Regression test T-n could not be verified against the pre-fix state."
   - The regression test must exercise the exact input that triggered the bug, and assert the corrected output.

6. **Run the test in isolation.** Execute the individual test to verify it passes:
   - If the test passes, record the result.
   - If the test fails, diagnose: is the test wrong (doesn't match T-n), or is the implementation wrong (doesn't satisfy T-n)?
     - If the test doesn't match T-n: fix the test.
     - If the implementation doesn't satisfy T-n: trace back to the CH-n that owns this behavior and fix the implementation (return to Gate 3 for that CH-n).

### Stop when
- The test passes in isolation
- The test uses the exact input from T-n
- The test asserts the exact expected output from T-n
- The test follows local test patterns (naming, fixtures, assertions, organization)
- The test is placed in the correct test file

### Common failures
- **Loose assertions**: Asserting `result is not None` or `status == 200` when T-n specifies an exact value. Fix: Always use the exact expected output from T-n as the assertion.
- **Test coupling**: Writing a test that depends on another test's side effects (shared mutable state, database rows from a previous test). Fix: Each test must set up its own state and clean up after itself.
- **Style mismatch**: Using a different assertion library or test organization than the rest of the test file. Fix: Consult the pattern inventory before writing any test code.
- **Fixture duplication**: Creating a new factory/fixture that does the same thing as an existing one. Fix: Search for existing fixtures before creating new ones.
- **Testing the implementation, not the behavior**: Asserting that specific internal functions were called instead of asserting the observable output. Fix: Assert what the user/caller sees, not how the code internally works (unless the plan explicitly requires it).

---

## Verification Protocol

### When to use
Gate 5 (Verification) for every plan, after all CH-n and T-n items are implemented.

### Steps

1. **Confirm per-CH smoke checks.** Review the smoke check results from Gate 3. Every CH-n should have a recorded smoke check result (pass, fail, or skipped with reason). If any were skipped, run them now.

2. **Execute all T-n tests.** Run every test specified in the plan:
   - Run each T-n test individually first to confirm isolation.
   - Then run all T-n tests together to catch ordering/state dependencies.
   - Record the result for each T-n: pass or fail with output.
   - For each failing T-n, proceed to the failure triage protocol (step 6).

3. **Run broader regression tests.** Run the test suite for every module affected by the plan's changes:
   - If the plan specifies test commands, run those exact commands.
   - If the plan does not specify commands, run the standard test command for the affected modules (e.g., `pytest tests/module/`, `npm test -- --testPathPattern=module`).
   - Record: number of tests run, number passed, number failed, any new failures.

4. **Run type and lint checks.** If the project has configured type checkers or linters:
   - Run the type checker on all changed files (e.g., `tsc --noEmit`, `mypy changed_files`, `pyright`).
   - Run the linter on all changed files (e.g., `eslint`, `flake8`, `rubocop`).
   - Record: number of errors, number of warnings, whether any are new (not pre-existing).
   - New type errors in changed files are implementation bugs. New type errors in unchanged files are propagation errors.

5. **Run plan-specified verification commands.** Execute any additional commands from the plan's Verification section that haven't been covered by steps 2–4. These are mandatory. Record the output.

6. **Failure triage protocol.** For each failure encountered in steps 2–5:

   a. **T-n test failure**:
      - Compare the failing assertion to the T-n specification. Does the test match what T-n requires?
      - If the test matches T-n but fails: the implementation has a bug. Identify which CH-n owns the failing behavior. Return to Gate 3 for that CH-n and fix it.
      - If the test does not match T-n: the test has a bug. Return to Gate 4 for that T-n and fix the test.

   b. **Regression test failure** (existing test, not a T-n test):
      - Determine if the failure is caused by the plan's changes or is pre-existing.
      - Check: was this test passing before the plan's changes? (Use `git stash` or `git diff` to verify if practical.)
      - If pre-existing: record the failure as pre-existing and continue. Do not fix it — it is out of scope.
      - If caused by the plan's changes: identify which CH-n broke it. Check the plan's propagation map — is the broken test accounted for? If yes, fix per the plan. If no, this is an under-specified propagation — record it and fix if the fix is obvious and minimal. If the fix is non-trivial, trigger the Rollback Protocol.

   c. **Type/lint failure**:
      - If the error is in a file you changed: it is an implementation bug. Fix it.
      - If the error is in a file you did NOT change: it is a propagation error. A symbol you changed is used in that file, and the file was not updated. Check the plan's propagation map — if the file is listed, apply the planned update. If the file is not listed, this is an under-specified propagation. Record it and fix if minimal, or trigger the Rollback Protocol.

7. **Iterate until clean.** After fixing any failures, re-run the failed checks. Do not proceed to the Report gate until all checks pass or all failures are triaged and recorded.

### Stop when
- All T-n tests pass
- No new regressions in touched modules (pre-existing failures are recorded but not blocking)
- No new type/lint errors in changed files
- All plan-specified verification commands have been run and their output recorded
- Every failure has been triaged: fixed, recorded as pre-existing, or escalated via Rollback Protocol

### Common failures
- **Partial test runs**: Running only the new T-n tests and not the existing module tests. Fix: Always run the full test suite for affected modules.
- **Ignoring type/lint errors**: Treating type checker warnings as non-blocking when they indicate real propagation bugs. Fix: New type errors in changed files must be fixed before proceeding.
- **False-positive regression claims**: Treating a pre-existing failure as caused by the plan's changes. Fix: Always check the pre-change state before attributing blame.
- **Skipping plan-specified commands**: Forgetting to run commands from the plan's Verification section. Fix: These are mandatory — check the plan's Verification section explicitly before leaving Gate 5.

---

## Rollback Protocol

### When to use
When a plan-repo contradiction is discovered mid-implementation, or when a CH-n cannot be applied as specified, or when verification reveals a non-trivial propagation error not covered by the plan.

### Steps

1. **Stop editing immediately.** Do not attempt to fix the contradiction by improvising, expanding scope, or reinterpreting the plan. The plan is a contract. If the contract cannot be fulfilled as written, the contract must be updated.

2. **Record the contradiction.** Document precisely:
   - Which CH-n conflicted or could not be applied.
   - What the plan expected (cite the plan's specification).
   - What the repo actually contains (cite `file:line`).
   - Why the plan cannot be applied as written (the specific mismatch).
   - Examples of contradictions:
     - The plan says to modify function `foo()` in `bar.py`, but `foo()` does not exist or has a different signature.
     - The plan says to add a parameter to an interface, but the interface has already been changed by a recent commit not reflected in the plan.
     - A CH-n depends on a library feature that is not available in the installed version.
     - The plan's propagation map is missing callers that exist in the repo.

3. **Assess partial state.** Determine the safety of already-applied changes:
   - List every CH-n that has been applied so far.
   - For each applied CH-n, ask: is this change independently correct and safe WITHOUT the blocked CH-n?
     - **Independently correct**: The change compiles, passes its smoke check, and does not break existing behavior.
     - **NOT independently correct**: The change depends on the blocked CH-n (e.g., it calls a function that the blocked CH-n was supposed to create, or it uses a type that the blocked CH-n was supposed to define).
   - Classify each applied CH-n as **keep** or **revert**.

4. **Revert if necessary.** If any applied CH-n items are not independently correct:
   - Use `git checkout -- <file>` or `git restore <file>` to revert changed files.
   - If changes span multiple files and some are safe to keep, use targeted reverts per file.
   - After reverting, verify the workspace is clean: run the smoke checks that were passing before implementation started.
   - If using a branch, consider reverting to the branch point.

5. **Report the contradiction.** Communicate to the user:
   - **What happened**: Which CH-n conflicted and why.
   - **What was applied**: Which CH-n items were successfully applied (if any are being kept).
   - **What was reverted**: Which CH-n items were reverted and why.
   - **Current state**: The workspace is in a clean, consistent state — either all changes applied, all changes reverted, or only independently-correct changes retained.
   - **Recommendation**: Update the plan via `plan-with-senior-dev` to account for the repo's actual state before retrying implementation.

6. **Do NOT improvise a fix.** Specifically, do not:
   - Guess what the plan "probably meant" and implement that instead.
   - Add new symbols, functions, or behavior not in the plan to work around the contradiction.
   - Modify the plan's specification unilaterally (e.g., changing a function signature to match what the repo has).
   - Skip the blocked CH-n and continue with downstream CH-n items that depend on it.
   - "Fix it and document the deviation" — deviations compound and the downstream effects are not analyzed.
   The only safe action is to stop, revert if needed, and report.

### Stop when
- The workspace is in a clean, consistent state:
  - **All changes applied**: The contradiction was in a non-blocking CH-n and all other changes are independently correct, OR
  - **All changes reverted**: The contradiction affects the foundation and no partial state is safe, OR
  - **Only independently-correct changes retained**: Some CH-n items are safe without the blocked one
- The contradiction is fully documented with plan citations and repo citations
- The user has been informed with a clear recommendation

### Common failures
- **Improvising a fix**: Attempting to resolve the contradiction by expanding scope or inventing behavior. This is the most dangerous failure — it produces code that no plan authorized and no verification matrix covers. Fix: Stop and report.
- **Half-applied state**: Leaving the workspace with some CH-n items applied and some not, without verifying that the applied items are independently correct. Fix: Always assess partial state and either keep or revert each applied CH-n.
- **Silent workaround**: Adjusting the implementation to fit the repo without recording the deviation. Fix: Every deviation from the plan must be reported, even if the "fix" seems obvious.
- **Continuing past the contradiction**: Implementing downstream CH-n items that depend on the blocked CH-n. Fix: If a CH-n is blocked, everything that depends on it in the dependency graph is also blocked.
