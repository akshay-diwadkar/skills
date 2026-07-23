# Code Quality Checklist

> Run this checklist against every file edited during implementation.
> Every item is a yes/no gate. A "no" requires either a fix or an explicit justification traced to the plan.

---

## 1. Style Consistency

- [ ] Naming conventions (casing, prefixes, suffixes) match the file's existing style, not your preferred style
- [ ] Import organization (grouping, ordering, blank lines between groups) follows the file's existing pattern
- [ ] Indentation (tabs vs spaces, width) matches the file's existing pattern
- [ ] Bracket/brace placement (same-line vs next-line) matches the file's existing pattern
- [ ] String quote style (single vs double) matches the file's existing pattern
- [ ] Line length stays within the file's prevailing limit
- [ ] No trailing whitespace introduced on any line
- [ ] No formatting changes to lines not touched by the plan

---

## 2. Error Handling Completeness

- [ ] Every error path specified in the plan's pseudocode exists in the implementation
- [ ] Every `else` / `default` / fallback branch specified in the plan exists
- [ ] Error types and error codes match what the plan specifies — no generic `Error` or `Exception` substitutions
- [ ] Error messages are specific and match plan specifications (not placeholder text)
- [ ] No swallowed exceptions or silent failures unless the plan explicitly specifies them
- [ ] `finally` / cleanup / rollback logic exists where the plan specifies side effects that need unwinding
- [ ] Async error paths (rejected promises, errbacks, error channels) are handled, not just sync throws

---

## 3. Type Safety

- [ ] No `any`, `Object`, `unknown`, `interface{}`, or language-equivalent where the plan specifies a concrete type
- [ ] No implicit type coercions that could lose data (e.g., float → int, string → number)
- [ ] Nullability matches the plan: nullable where the plan says nullable, non-null where the plan says non-null
- [ ] Generic type parameters match the plan's specifications exactly
- [ ] Return types match the plan's signatures — no widened or narrowed types
- [ ] Union/enum variants match the plan's set — no extra or missing members
- [ ] Type assertions / casts are used only where the plan justifies them

---

## 4. Interface Fidelity

- [ ] Function/method signatures match the plan exactly: name, parameter order, types, defaults, return type
- [ ] New parameters have default values when the plan specifies them (to avoid breaking existing callers)
- [ ] Serialization format matches the plan: JSON keys, field names, wire types, enums
- [ ] Every caller named by a canonical `CH-n`, trace row, or accepted mechanical-propagation record has been updated
- [ ] No signature changes beyond what the plan specifies
- [ ] Public API surface (exports, visibility modifiers) matches the plan
- [ ] Deprecation markers are added where the plan specifies them

---

## 5. Test Quality

- [ ] Test names describe the **behavior** being verified, not the function name
- [ ] Assertions use the **exact** expected values from the plan's T-n specifications
- [ ] No approximate assertions (`contains`, `truthy`, `not-null`, `toBeGreaterThan`) where the plan specifies an exact value
- [ ] Fixtures are minimal — only the data needed for the specific test case
- [ ] Existing fixtures are reused when they already match the needed shape
- [ ] Each test is independent — no reliance on execution order or shared mutable state
- [ ] Negative / error tests assert the **specific** error type and message, not just "throws"
- [ ] Edge cases listed in the plan's T-n specs have corresponding test cases
- [ ] No test logic (conditionals, loops) — tests are straight-line: arrange → act → assert

---

## 6. Invariant Preservation

- [ ] Existing behavior **not mentioned** in the plan is unchanged
- [ ] Existing comments and docstrings unrelated to the change are preserved verbatim
- [ ] Existing tests that should continue passing are not modified
- [ ] No opportunistic cleanup, renaming, or reformatting of untouched code
- [ ] No new abstractions (classes, interfaces, helpers) unless the plan explicitly requires them
- [ ] Existing log statements, metrics, and telemetry calls are preserved unless the plan modifies them
- [ ] Existing error messages in untouched paths are preserved
- [ ] File-level structure (class order, function order, section separators) is preserved

---

## 7. Scope Discipline

- [ ] Every changed line traces to a `CH-n` as planned work or passes the canonical Mechanical Propagation Gate
- [ ] Every unplanned file is recorded as `mechanical-propagation` with policy flags, evidence, and verification
- [ ] No new dependencies (packages, modules, imports from new files) unless the plan specifies them
- [ ] Generated artifacts are plan-named or deterministic, bounded mechanical output with no unexplained dependency/version churn
- [ ] No formatting-only changes mixed with logic changes in the same commit
- [ ] No TODO/FIXME comments added unless the plan explicitly includes them
- [ ] No dead code introduced (unused imports, unreachable branches, commented-out blocks)
- [ ] Initial unrelated dirty paths retain their recorded hashes
- [ ] No automatic whole-file, worktree, commit, or branch restoration was used

---

## 8. Completeness

- [ ] Every `CH-n` in the plan has a corresponding implementation
- [ ] Every `T-n` in the plan has a corresponding test
- [ ] Every caller, fixture, config, schema, generated surface, and documentation impact named by the plan has been addressed
- [ ] Every constraint (`C-n`) marked `at-risk` has been verified against the implementation
- [ ] Every risk (`R-n`) with `P0` or `P1` severity has its mitigation implemented
- [ ] All plan-specified validation logic (input checks, boundary conditions) is present
- [ ] No partial implementations — each `CH-n` is fully done or fully deferred with justification
- [ ] The implementation bundle accounts for every `CH-n`, `T-n`, changed path, command, deviation, and residual risk
- [ ] `finalize_implementation.py` passes and stamps a validation receipt before status is reported as `complete`

---

## Quick Reference: Common Violations

| Violation | Checklist Section |
|---|---|
| Changed indentation in untouched lines | §1 Style, §6 Invariant |
| Generic `catch (e)` without typed handling | §2 Error Handling |
| Used `any` for convenience | §3 Type Safety |
| Added parameter without default | §4 Interface Fidelity |
| Test asserts `toBeTruthy()` instead of exact value | §5 Test Quality |
| Renamed a variable "while I was in there" | §6 Invariant, §7 Scope |
| Edited an unplanned file without passing the Mechanical Propagation Gate | §7 Scope |
| Skipped a `CH-n` without justification | §8 Completeness |
