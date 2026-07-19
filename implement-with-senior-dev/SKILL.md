---
name: implement-with-senior-dev
description: Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report. Use when the user has an approved or written plan and asks to implement, apply, or build it. Vague plans are refused back to planning.
---

# Implement With Senior Dev

Implement the approved plan as the smallest complete patch. Repository evidence decides how code is written; the plan decides what behavior may change; the implementation contract proves what actually happened.

## Read Before Acting

Read these files completely before editing:

1. `references/implementation-contract.json` — authoritative run-bundle fields, statuses, and safety policy.
2. `references/implementation-protocols.md` — canonical intake, editing, propagation, verification, and recovery procedure.
3. `references/code-quality-checklist.md` — per-file and final quality gates.
4. `references/implementation-hazards.md` — exact stop/recovery decisions.

## Non-Negotiables

- Identify and snapshot the exact approved plan before editing.
- Prefer `plan-contract: 2` metadata and anchor-based records. Use the strict legacy adapter only when no version marker exists.
- Refuse a plan when the parser reports ambiguity or a material repository contradiction.
- Never use an implementation interview to reinterpret, repair, or extend approved product intent. Record semantic gaps and route them to `plan-with-senior-dev`; ask only for execution-state authorization already permitted by this contract.
- Create an implementation-run bundle in confirmed ignored storage or an OS temporary directory.
- Preserve unrelated dirty paths byte-for-byte. Never edit a dirty target without explicit user authorization.
- Recheck a target against the last recorded snapshot before every edit; stop on concurrent changes.
- Apply planned changes in dependency order and implement every specified branch, error, side effect, and test.
- Allow unplanned edits only under the Mechanical Propagation Gate in the canonical protocol.
- Attribute a failure as pre-existing only when the exact check failed in the recorded pre-edit baseline; otherwise use `unknown-baseline`.
- Reverse only positively identified agent-owned hunks whose current context still matches. Never perform automatic whole-file, worktree, or branch restoration.
- Run the implementation checker before claiming completion.

## Execution Gates

### 1. Normalize the Plan

Save conversational plans verbatim to the run directory. Parse the plan with `implementation_contract.parse_plan`.

- Versioned plans: require `<!-- plan-contract: 2 -->`, the explicit tier/task marker, canonical `SC/CH/T` records, and traceability.
- Legacy ID plans: require unambiguous `SC/CH/T` records, target paths, verification commands, and traceability.
- Legacy Tiny plans: require concrete Outcome/Goal, Scope, Change/Implementation, and Verification/Test sections, plus a target path and command.

Stop with field-specific diagnostics when parsing fails. Do not reinterpret the plan.

If inspection exposes a semantic contradiction or a choice affecting product behavior, failure semantics, contracts, persistence, dependencies, migration, or external effects, stop and hand the evidence back to `plan-with-senior-dev`. Dirty-target incorporation and explicitly scoped unsafe/external-operation authorization remain execution questions; their answers do not revise the plan.

### 2. Scaffold and Inspect

Create the run bundle:

```bash
python scripts/scaffold_implementation.py \
  --repo-root <repo> \
  --plan <run-dir>/plan.md \
  --output <run-dir>/implementation.json
```

Use `.scratch/implement-with-senior-dev/<run-id>/` only when `git check-ignore` confirms it is ignored; otherwise use an OS temporary directory.

Before editing:

- Inspect repository guidance, status, manifests, affected code, callers, tests, fixtures, configuration, and generated surfaces.
- Record local naming, imports, errors, logging, comments, test, and analogue patterns.
- Run safe focused baseline checks when practical and record their command, exit code, and evidence.
- Stop on dirty plan targets unless the bundle records explicit user authorization.

### 3. Implement in Dependency Order

For each `CH-n`:

1. Re-read its exact path, anchor, behavior, branches, errors, ordering, and side effects.
2. Verify the target still matches the last snapshot.
3. Apply the smallest edit following the nearest repository analogue.
4. Record a `planned` change with its `CH-n`, paths, anchors, before/after hashes, and evidence.
5. Run the narrowest useful smoke check and record its evidence.

If an omitted caller, fixture, or compatibility edit appears, apply the Mechanical Propagation Gate before touching it.

### 4. Implement Tests

Translate every `T-n` into the repository's existing test style. Use its exact setup/input and observable output, error, or side effect. Prefer behavioral assertions over internal-call assertions unless the plan explicitly specifies the interaction.

Run focused tests individually, then together. Record the command, expected result, actual exit code, evidence path, linked `T-n`, and status.

### 5. Verify and Reconcile

Run, in order:

1. Every plan `T-n` command.
2. Regression tests for affected modules.
3. Configured type and lint checks for changed surfaces.
4. Every additional plan-specified command.

Reconcile actual workspace status against the initial bundle. Every new changed path must be covered by a `planned` or `mechanical-propagation` record. Initial unrelated dirty paths must retain their original hashes.

### 6. Validate Completion

Finalize `status`, unresolved `CH/T` records, final changed paths, deviations, residual risks, and report summary. Then run:

```bash
python scripts/check_implementation.py \
  --repo-root <repo> \
  --plan <run-dir>/plan.md \
  <run-dir>/implementation.json
```

Use `complete` only when the checker passes, every `CH/T` is accounted for, required verification passed, and the final delta is fully declared. Use `partial` or `blocked` only with exact unresolved records and a safe workspace.

### 7. Report

Report:

- Plan source, contract version, and tier.
- Planned changes by `CH-n`, path, and anchor.
- Mechanical propagation with owning `CH-n`, evidence, and verification.
- Commands and exact results, including skipped or blocked checks.
- Final status, residual risks, unresolved records, and required follow-up.

Never claim weaker-model reliability unless the provider-neutral live evaluation suite has completed for the named model with no hard failures, median score at least 90, and every run at least 80.

## Handoffs

- Use `plan-with-senior-dev` when the approved input cannot pass strict intake.
- Use `plan-with-senior-dev` when repository evidence exposes a semantic plan gap; do not grill the user to repair approved intent inside implementation.
- Use `codebase-issue-auditor` to discover unknown risks instead of implementing a known change.
- Use `optimize-codebase-with-senior-dev` when selecting or measuring an optimization rather than applying an approved implementation plan.
