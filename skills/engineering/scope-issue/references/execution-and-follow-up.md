# Execution and Follow-up

Planning does not authorize execution. Execute one issue per branch only after
explicit user authorization and a validator-passing current artifact.

## Freshness gate

1. Re-fetch the selected issue into a fresh immutable JSON file.
2. Inspect `git status -sb` and existing diffs; preserve unrelated work.
3. Run `check_issue_plan.py` with `--execution-ready`, the current repository,
   and fresh issue JSON. For `ready-for-senior-plan`, also supply the finalized
   v5 senior plan.
4. Fail closed when the checker or senior skill is unavailable.
5. If updating the base branch changes `HEAD`, regenerate the issue artifact.

## Branch and pull request

Create `codex/issue-<number>-<slug>`, implement only that issue, and run the
artifact's exact checks plus focused affected tests. Commit as
`Fix issue #<number>: <short title>` and open a ready-for-review PR titled
`[codex] Issue #<number>: <title>`.

Use `Refs #<number>`, never an auto-close keyword. Include validation,
assumptions, artifact path, and the resumable post-merge command. Never batch
issues into one branch or PR.

## Post-merge

After approval and merge, update the expected base, rerun recorded checks, and
write a verification summary. Run `scripts/post_merge_issue_followup.py` with
the approved repository, issue, PR, base, environment, and summary.

The script verifies merge, base, approval, issue reference and identity, and an
idempotency marker before posting one comment. It never closes or labels the
issue. Do not comment through another path.
