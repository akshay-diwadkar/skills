# Implementation Hazards Catalog

Common failure modes that occur **during implementation** of approved plans,
with detection signals and concrete recovery procedures.

> Each hazard is something that can go wrong while applying CH-n items.
> These are not abstract risks — they are situations you will encounter.
> When you hit one, follow the recovery procedure exactly.

---

## 1. Partial Patch State

**Situation**: CH-3 fails or reveals a contradiction after CH-1 and CH-2 have
already been applied.

**Detection**: A CH-n cannot be applied as specified — the target symbol doesn't
exist, the file structure doesn't match, or the change would conflict with
another CH-n's changes.

**Recovery**:
- Assess whether already-applied CH-n items are independently correct without
  the blocked CH-n
- If they are: keep them, report the blocked CH-n and its reason, recommend
  plan revision for the blocked portion
- If they are NOT (e.g., CH-1 added a type that CH-3 was supposed to use, and
  without CH-3 the type is orphaned): revert all changes back to the clean state
- Never leave the workspace with orphaned symbols, broken imports, or
  half-updated callers

**Prevention**: Gate 1 (Plan Intake) catches most dependency issues by building
the dependency graph before editing.

---

## 2. Plan-Repo Contradiction

**Situation**: The plan cites `file:line` that doesn't match current repo state.
A function the plan says to modify has been renamed, moved, or deleted. The plan
assumes a dependency/config that doesn't exist.

**Detection**: During Gate 2 (Workspace Reconnaissance) or Gate 3
(Implementation) — the cited code doesn't exist or behaves differently than the
plan describes.

**Recovery**:
- Record the exact contradiction: what the plan says vs what the repo shows
- Classify severity:
  - **Cosmetic** — line numbers shifted but code is the same → adapt silently
  - **Material** — code logic changed → stop and report
  - **Blocking** — symbol deleted or renamed → cannot proceed
- For cosmetic contradictions: adapt the line numbers and continue, noting the
  discrepancy in the report
- For material/blocking contradictions: stop implementation, report the
  contradiction, recommend re-running `plan-with-senior-dev`
- Do NOT improvise fixes to material contradictions

**Prevention**: Plans should be implemented promptly after approval; stale plans
accumulate contradictions.

---

## 3. Test Fixture Drift

**Situation**: Existing test fixtures assume the old behavior/interface. After
applying CH-n changes, existing tests that use these fixtures break — not because
the implementation is wrong, but because the fixtures encode the old shape.

**Detection**: Existing tests fail after implementation, and the failures are in
fixture setup or assertion expectations that reference old interfaces.

**Recovery**:
- Check the plan's propagation map — if the plan listed these test fixtures
  under "update required: yes", update them as specified
- If the plan did NOT list the affected fixtures, this is a plan gap. Record it
  and update the fixtures minimally to match the new interface, only if the
  change is clearly mechanical (e.g., adding a new required field with the
  plan-specified default)
- If the fixture update requires judgment beyond what the plan specifies, stop
  and report

**Prevention**: The plan's propagation discovery should have caught test
fixtures. Report the gap for future plan quality improvement.

---

## 4. Generated Artifact Conflicts

**Situation**: Implementation changes trigger regeneration of lockfiles,
migration files, snapshot files, OpenAPI specs, protobuf outputs, or other
generated artifacts. The generated output conflicts with existing content or
requires manual resolution.

**Detection**: Build/test commands fail with complaints about out-of-date
generated files, or generated file diffs contain unexpected changes beyond what
the plan specified.

**Recovery**:
- If the plan explicitly names the generated artifacts: regenerate them as
  specified
- If the plan does NOT name them but they are mechanically derived from plan
  changes (e.g., lockfile updates after adding a dependency the plan specified):
  regenerate them and note in the report
- If regeneration produces unexpected changes beyond the plan scope (e.g., a
  lockfile update pulls in 50 new transitive dependencies): stop, report the
  situation, and let the user decide
- Never commit generated artifact changes that you don't understand

**Prevention**: Plans for changes that affect generated artifacts should
explicitly list the regeneration steps.

---

## 5. Merge Conflicts with In-Flight User Changes

**Situation**: The user has uncommitted changes in files that the plan targets,
or makes changes to the same files while implementation is in progress.

**Detection**: During Gate 2 (Workspace Reconnaissance) — dirty worktree
detected in plan-targeted files. Or during implementation — file contents don't
match what you just wrote.

**Recovery**:
- If detected in Gate 2: report the dirty files, ask the user whether to
  proceed (their changes may be intentional context) or wait
- If detected during implementation: stop, do not overwrite user changes, report
  the conflict
- Never silently overwrite uncommitted user changes

**Prevention**: Gate 2 checks worktree cleanliness before editing.

---

## 6. Missing Dependencies or Secrets

**Situation**: The plan assumes a package/module/service/API key/environment
variable that doesn't exist in the workspace.

**Detection**: Import errors, build failures referencing missing modules, runtime
config errors for missing env vars.

**Recovery**:
- If the plan explicitly lists the dependency installation step: follow it
- If the plan assumes the dependency exists but it doesn't: stop and report. Do
  not install dependencies the plan didn't specify
- For missing secrets/env vars: stop and report. Never create placeholder
  secrets or mock credentials

**Prevention**: Gate 2 should verify that all imports and dependencies referenced
in CH-n items exist.

---

## 7. Build or Type Errors from Incomplete Propagation

**Situation**: After applying all CH-n items, the project has type errors or
build failures in files that were NOT listed in the plan's changes.

**Detection**: Type checker or compiler reports errors in files you didn't edit.

**Recovery**:
- Trace the error to its cause: which CH-n changed a symbol that this file
  depends on?
- Check the plan's propagation map — was this file listed under "update
  required: yes"? If so, this is a plan gap (the propagation was identified but
  no CH-n was assigned). Apply the minimal mechanical fix and note it
- If the file was NOT in the propagation map, this is a more serious plan gap.
  Apply the minimal fix only if it's clearly mechanical (e.g., adding a
  newly-required argument with the plan-specified default). Otherwise stop and
  report
- Record all unplanned fixes in the report as scope additions with
  justification

**Prevention**: Plan's Gate 6 (Attack and Repair) should have caught forgotten
callers via A1.

---

## 8. Circular or Impossible Dependency Order

**Situation**: The CH-n dependency graph built in Gate 1 reveals a cycle, or
applying CH-n items in the planned order is impossible because of mutual
dependencies.

**Detection**: During Gate 1 (Plan Intake) — the dependency graph has a cycle,
or during Gate 3 — a CH-n requires a symbol that a later CH-n introduces.

**Recovery**:
- Check if the cycle is an artifact of your dependency analysis (false positive)
- If the cycle is real: can the changes be combined into a single atomic edit?
  If so, combine and note it
- If they cannot be combined: report the impossible ordering and recommend plan
  revision

**Prevention**: Well-structured plans order changes by dependency layer
(contracts → core → callers → tests).

---

## 9. Performance or Resource Concerns During Verification

**Situation**: Verification commands take unexpectedly long, consume excessive
memory, or time out.

**Detection**: Test suite hangs, OOM errors, or verification commands run for
>5x the expected duration.

**Recovery**:
- Run the narrowest possible verification first (single test file, not full
  suite)
- If the narrowest verification succeeds, expand gradually
- If even narrow verification has issues: check if the implementation introduced
  an infinite loop, unbounded recursion, or N+1 query
- Report the verification limitation in the final report with what was verified
  and what was skipped

**Prevention**: Start with focused verification and expand, not the reverse.
