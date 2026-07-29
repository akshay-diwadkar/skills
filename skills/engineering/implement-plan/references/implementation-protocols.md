# Implementation Protocols

This is the canonical decision procedure for an implementation run.
`implementation-contract.json` v3 is authoritative for nested row schemas,
field names, enumerations, workspace reconciliation, and receipt policy.

## 1. Plan Normalization Protocol

1. Save the approved plan verbatim. Never summarize away constraints or verification details.
2. Parse metadata before content:
   - Require a version listed in `supported_plan_contract_versions` or `deprecated_plan_contract_versions`, strict metadata, the complete typed record graph, targeted repository binding, and that version's finalizer receipt.
   - Persist and print `bundle.plan_contract_deprecated` when the version is deprecated.
   - Reject unlisted and unversioned plans with `contract.unsupported`.
3. Reject unsupported or unfinalized plan versions instead of guessing forward compatibility. A deprecated warning is reviewable but non-blocking.
4. Build registries for `SC-n`, `CH-n`, `T-n`, `C-n`, and `R-n`, plus traceability rows.
5. Order `CH-n` records by dependency: contracts/data → core logic → orchestration/callers → tests/fixtures → generated/docs/operations.
6. Refuse when a referenced record is missing, a `CH-n` lacks a target path, a `T-n` lacks a command, or a change/test is untraced.
7. For High-Risk plans, require Compatibility and Rollout plus Durable Rollback sections.

The parser's diagnostics are blocking. Do not repair or reinterpret an approved plan during implementation.

Repository contradictions and semantic gaps are also blocking. Record the affected plan records, plan expectation, repository evidence, and consequence, then route the gap to `plan-change`. Do not present behavior options or conduct an intent-revision interview from the implementation skill. Only ask for execution-state authorization explicitly recognized by this protocol, such as incorporating an already dirty target; such authorization never changes planned behavior.

## 2. Run Bundle and Workspace Baseline

1. Resolve storage:
   - Use repository-local `.scratch/implement-plan/<run-id>/` only after `git check-ignore` succeeds for the intended bundle path.
   - Otherwise use an OS temporary directory.
2. Scaffold the bundle before editing. Preserve the plan snapshot and immutable target before-copies under `snapshots/` beside it; new targets receive empty snapshots.
3. Record commit, branch, initial status, content hashes of dirty paths, target existence/hashes/status, and safe baseline commands.
4. Unrelated dirty paths are allowed and protected. A dirty target is blocking unless the user explicitly authorizes incorporating it and the bundle records `user-authorized`.
5. Read affected symbols, callers, tests, fixtures, configs, schemas, generated artifacts, and nearest analogues. Record conventions rather than relying on memory.
6. Before each edit, compare the file with the last recorded snapshot. A mismatch means concurrent modification: stop and follow the recovery protocol.

## 3. Planned Change Protocol

For each dependency-ordered `CH-n`:

1. Re-read the canonical record and applicable constraints/risks.
2. Confirm path and anchor still match repository reality. Shifted lines are cosmetic; changed behavior or missing anchors are material.
3. Apply only the specified behavior using local naming, import, error, logging, comment, and test patterns.
4. Implement every specified happy, error, else/default, boundary, cleanup, and async path.
5. Record a `planned` change containing the owning `CH-n`, paths, anchors, before/after hashes, evidence, and smoke verification.
6. Generate its optional `unified_diff` from the scaffolded before-copy and current file with `record_change_diff.py`. Treat the diff as human-review metadata; hashes remain authoritative and the validator never grades diff content.
7. Re-read the resulting file and run the per-file quality checklist.

## 4. Mechanical Propagation Gate

An unplanned edit is allowed only when every answer is **yes**:

| Decision | Required answer |
|---|---|
| Is it directly caused by an approved `CH-n`? | Yes |
| Is the transformation deterministic from the approved interface, schema, or default? | Yes |
| Does it avoid every product or failure-semantics decision? | Yes |
| Does it avoid a new dependency or abstraction? | Yes |
| Does it avoid a new public/shared contract? | Yes |
| Does it avoid migration, destructive action, or external effect? | Yes |
| Is it necessary for compile, type-check, or existing-test compatibility? | Yes |

When all answers are yes:

- Record `kind: mechanical-propagation`, the owning `CH-n`, exact paths, all policy flags, necessity reason, evidence, and verification.
- Apply the smallest mechanical edit.
- Report it as a plan gap, not as planned scope.

Stop instead when the edit changes product behavior, unspecified expected assertions, dependencies, public contracts, persistence, external effects, authorization, generated dependency resolution, or requires choosing among alternatives.

For these semantic stops, preserve the evidence and hand off to `plan-change`; do not resolve alternatives through implementation questioning.

Generated artifacts may be updated only when named by the plan or produced deterministically by a plan-specified command with an understood and bounded diff. Unexpected generated output is blocking.

## 5. Test Translation and Verification

1. Translate each `T-n` using its exact setup/input and expected observable result.
2. Follow the local test structure, fixtures, mocks, naming, and assertion style.
3. Run each focused test independently, then all plan tests together, affected-module regression tests, configured type/lint checks, and remaining plan commands.
4. Store command, expected result, actual exit code, status, evidence path, and linked `T-n` records.
5. For every configured lint/type tool relevant to a touched language, store a `quality_checks` row with the exact changed paths and their current SHA-256 hashes. Cite only checklist sections 1-4.
6. When no configured tool exists, store a skipped row with exit code 127 and evidence naming the unavailable gate. This is recorded evidence, not a completion waiver.
7. Never infer a command result from partial output. `passed` requires exit code zero and the expected observable result.
8. A failure is `pre-existing` only if the identical tool and command failed in the recorded pre-edit baseline. Without that evidence, classify it as `unknown-baseline` and investigate without changing unrelated code.
9. If a failure exposes omitted propagation, run the Mechanical Propagation Gate. If any answer is no, stop.

## 6. Non-Destructive Recovery

1. Stop editing on a material contradiction, concurrent modification, semantic plan gap, unexpected generated diff, or unsafe operation.
2. Record the blocked `CH/T`, plan expectation, repository evidence, and impact.
3. Classify applied changes as independently safe or dependent on blocked work.
4. Keep independently safe changes only when they compile, pass their focused checks, and introduce no orphaned symbols.
5. Reverse dependent work only when the run ledger identifies the exact agent-owned hunks and the current file still matches their recorded after-context.
6. Apply a reverse patch limited to those hunks. Never restore an entire file, worktree, index, commit, or branch automatically.
7. If ownership or current context cannot be proven, do not modify the file. Report the partial state and request direction.
8. Re-run the last known-safe checks after any proven hunk reversal.

## 7. Final Reconciliation

1. Map every plan `CH-n` to implemented change records or `unresolved_changes`.
2. Map every `T-n` to verification records or `unresolved_tests`.
3. Compare current status with the initial status. Every new path must be declared; protected dirty paths must retain their hashes.
4. Apply the finalized tier profile. Tiny permits one aggregate change row and one successful plan-test row. Standard and High-Risk require one planned row per CH plus a distinct successful regression row with no T-n claims.
5. Verify constraints, P0/P1 mitigations, error/default paths, unused symbols, generated artifacts, and mechanical-propagation records.
6. Fill final status, changed paths, deviations, risks, and report summary. Empty deviation and residual-risk arrays are valid when truthful at every tier.
7. Run `finalize_implementation.py` and repair bundle or implementation omissions until it passes and stamps a validation receipt.
8. Report `complete` only after checker success. A blocked or partial run must leave exact unresolved records and a safe, accurately described workspace.
