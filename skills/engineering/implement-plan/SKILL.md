---
name: implement-plan
description: Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report. Use when the user has an approved or written plan and asks to implement, apply, or build it. Vague plans are refused back to planning.
version: 1.1.0
metadata:
  implementation-contract: "3"
  finalizer: "scripts/finalize_implementation.py"
  validation-required: "true"
---

# Implement Plan

Implement the approved plan as the smallest complete patch. Repository evidence decides how code is written; the plan decides what behavior may change; the implementation contract proves what actually happened.

## Common CLI

Use the skill-local common CLI as the primary interface. Pass the exact
finalized plan and choose a new run directory outside both the installed skill
and target repository:

```bash
python /absolute/skill-root/scripts/cli.py \
  --repo-root /absolute/path/to/repository \
  --run-dir /absolute/path/to/temporary-run \
  --input plan_file=/absolute/path/to/finalized-plan.md \
  --format json \
  doctor
```

Execute each returned `next_command.argv` directly with its returned `cwd`.
Read only the returned phase references and stop on every blocking reason. A
fresh bundle remains in phase `implementing` until `implementation.json` has
status `complete` and passes the authoritative validator. Completion requires
phase `complete` and a matching implementation-contract v3 receipt.

Common-CLI intake refuses a planned target that was already dirty. Explicitly
authorized incorporation remains available only through the direct
compatibility workflow because v3 has no receipt-bound authorization field.
See `references/cli-compatibility.md` for every existing direct entry point.

## Read Before Acting

Read these files completely before editing:

1. `references/implementation-contract.json` — authoritative run-bundle fields, statuses, and safety policy.
2. `references/implementation-protocols.md` — canonical intake, editing, propagation, verification, and recovery procedure.
3. `references/code-quality-checklist.md` — per-file and final quality gates.
4. `references/implementation-hazards.md` — exact stop/recovery decisions.

## Non-Negotiables

- Identify and snapshot the exact approved plan before editing.
  - Require a finalized supported or deprecated plan contract, the complete typed record graph, targeted repository binding, and its matching finalizer receipt. Reject unlisted versions and do not translate them.
- Refuse a plan when the parser reports ambiguity, unfinalized status, receipt mismatch, or a material repository contradiction.
- Never use an implementation interview to reinterpret, repair, or extend approved product intent. Record semantic gaps and route them to `plan-change`; ask only for execution-state authorization already permitted by this contract.
- Accept plan versions listed by the implementation contract as supported or deprecated. Deprecated versions scaffold with a non-blocking `bundle.plan_contract_deprecated` warning; every unlisted version is rejected.
- Create an implementation-run bundle in confirmed ignored storage or an OS temporary directory.
- Preserve unrelated dirty paths byte-for-byte. Never edit a dirty target without explicit user authorization.
- Recheck a target against the last recorded snapshot before every edit; stop on concurrent changes.
- Apply planned changes in dependency order and implement every specified branch, error, side effect, execution blueprint, and test.
- Allow unplanned edits only under the Mechanical Propagation Gate in the canonical protocol.
- Attribute a failure as pre-existing only when the exact check failed in the recorded pre-edit baseline; otherwise use `unknown-baseline`.
- Record configured lint and type checks in `quality_checks` with exact changed-path hashes. Missing, stale, failed, or unavailable quality evidence blocks completion.
- Reverse only positively identified agent-owned hunks whose current context still matches. Never perform automatic whole-file, worktree, or branch restoration.
- Run `finalize_implementation.py` to stamp a SHA-256 validation receipt into the bundle before claiming completion.

## Skill Directory Resolution

Execute bundled runtime commands with the active skill directory (the directory containing this `SKILL.md`) set as the process working directory:
- On Claude Code: set `cwd` to `"${CLAUDE_SKILL_DIR}"` (or the active skill directory) if running from an external working directory.
- On other platforms: execute commands with process `cwd` set to the active skill directory.
- Resolve `skill-root` as the directory containing `SKILL.md` and `repo-root` as the absolute target repository path.
- All non-script paths (target repository, plan, output, draft, payload, `.env`, issue JSON, run-dir) passed as arguments MUST be absolute paths.
- Fail closed if `skill-root` or `repo-root` cannot be resolved.
- Never write output or state files relative to the installed skill package directory.

## Execution Gates

### 1. Normalize the Plan

Save conversational plans verbatim to the run directory. Parse the plan with `implementation_contract.parse_plan`.

- Require a listed plan-contract marker, strict classification metadata, the complete typed record graph, a valid targeted repository binding, and the matching receipt. Revalidate bound evidence and targets before creating the run bundle.
- Stop with field-specific diagnostics when parsing or receipt validation fails. Reject all v1/v2/legacy plans. Do not reinterpret the plan.

If inspection exposes a semantic contradiction or a choice affecting product behavior, failure semantics, contracts, persistence, dependencies, migration, or external effects, stop and hand the evidence back to `plan-change`. Dirty-target incorporation and explicitly scoped unsafe/external-operation authorization remain execution questions; their answers do not revise the plan.

When `plan-change` raises its contract version, update this skill in three releases: add the new version to `supported_plan_contract_versions` while retaining its parser, move the previous version to `deprecated_plan_contract_versions` for one release, then remove the deprecated version and parser. Keep the two lists disjoint.

### 2. Scaffold and Inspect

Create the run bundle from the active skill directory:

```bash
python scripts/scaffold_implementation.py \
  --repo-root /absolute/path/to/repository \
  --plan /absolute/path/to/run-dir/plan.md \
  --output /absolute/path/to/run-dir/implementation.json
```

Use `.scratch/implement-plan/<run-id>/` only when `git check-ignore` confirms it is ignored; otherwise use an OS temporary directory.

Before editing:

- Inspect repository guidance, status, manifests, affected code, callers, tests, fixtures, configuration, and generated surfaces.
- Record local naming, imports, errors, logging, comments, test, and analogue patterns.
- Run safe focused baseline checks when practical and record their command, exit code, and evidence.
- Stop on dirty plan targets unless the bundle records explicit user authorization.

### 3. Implement in Dependency Order

For each `CH-n`:

1. Re-read its exact path, anchor, behavior, branches, errors, ordering, side effects, and corresponding Execution Blueprints (pseudocode, Mermaid diagrams, before/after shapes, or tables).
2. Verify the target still matches the last snapshot.
3. Apply the smallest edit following the nearest repository analogue and execution blueprint logic.
4. Record a `planned` change with its `CH-n`, paths, anchors, before/after hashes, and evidence.
5. After recording authoritative hashes, run `scripts/record_change_diff.py` for the change row. The resulting optional `unified_diff` is review metadata only.
6. Run the narrowest useful smoke check and record its evidence.

If an omitted caller, fixture, or compatibility edit appears, apply the Mechanical Propagation Gate before touching it.

Scaffolding stores immutable before-copies under `snapshots/` beside the bundle, including empty snapshots for new targets. Generate diffs only from those copies. Never use a diff to replace or override before/after hashes.

### 4. Implement Tests

Translate every `T-n` into the repository's existing test style. Use its exact setup/input and observable output, error, or side effect. Prefer behavioral assertions over internal-call assertions unless the plan explicitly specifies the interaction.

Run focused tests individually, then together. Record the command, expected result, actual exit code, evidence path, linked `T-n`, and status.

### 5. Verify and Reconcile

Run, in order:

1. Every plan `T-n` command.
2. Regression tests for affected modules.
3. Every configured type and lint check for each touched language. Record tool, command, exit code, status, evidence, checklist sections, covered paths, and their current SHA-256 hashes in `quality_checks`.
4. Every additional plan-specified command.

Classify a nonzero quality result as `pre-existing-failure` only when the identical tool and command has a nonzero, evidenced row in `baseline.quality_checks`. Use `unknown-baseline` otherwise. If no configured tool exists, record a `skipped` row with exit code 127 and the missing prerequisite; `bundle.quality_tool_unavailable` remains blocking.

Scale record ceremony from the finalized tier without relaxing integrity:

- Tiny may aggregate planned work into one change row and needs at least one successful plan-test command.
- Standard and High-Risk require one independent planned row per `CH-n` plus a distinct successful affected-module regression row. Regression rows use `kind: regression` and empty `t_ids`; they never satisfy plan-test accounting.
- Keep deviations and residual risks as arrays. Leave them empty when none exist; never fabricate records to satisfy a tier.

Reconcile actual workspace status against the initial bundle. Every new changed path must be covered by a `planned` or `mechanical-propagation` record. Initial unrelated dirty paths must retain their original hashes.

### 6. Validate Completion

Finalize `status`, unresolved `CH/T` records, final changed paths, deviations, residual risks, and report summary. Then run from the active skill directory:

```bash
python scripts/finalize_implementation.py \
  --repo-root /absolute/path/to/repository \
  --plan /absolute/path/to/run-dir/plan.md \
  /absolute/path/to/run-dir/implementation.json
```

The finalizer runs all bundle and workspace validation checks in-process. On success, it stamps a SHA-256 validation receipt (`validation_receipt`) into the bundle JSON. Submit only the finalized output. A failed or unfinalized bundle blocks implementation completion.

### 7. Report

Report:

- Plan source, contract version, and tier.
- Planned changes by `CH-n`, path, and anchor.
- Mechanical propagation with owning `CH-n`, evidence, and verification.
- Commands and exact results, including skipped or blocked checks.
- Final status, residual risks, unresolved records, and required follow-up.

Never claim weaker-model reliability unless the provider-neutral live evaluation suite has completed for the named model with no hard failures, median score at least 90, and every run at least 80.

## Handoffs

- Use `plan-change` when the approved input cannot pass strict intake.
- Use `plan-change` when repository evidence exposes a semantic plan gap; do not grill the user to repair approved intent inside implementation.
- Use `audit-codebase` to discover unknown risks instead of implementing a known change.
- Use `optimize-codebase` when selecting or measuring an optimization rather than applying an approved implementation plan.
