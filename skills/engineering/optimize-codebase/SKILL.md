---
name: optimize-codebase
description: Investigate a named performance, build, CI, dependency, maintainability, or developer-experience bottleneck and seal one evidence-backed optimization handoff for plan-change. Use targeted mode for a known pain and sweep mode only for explicit repository-wide discovery.
version: 4.0.2
metadata:
  invocation: user-invoked
disable-model-invocation: true
user-invocable: true
---

# Optimize Codebase

## Purpose and authority

Select one evidence-backed leverage point for a named workflow and seal one
`optimization-handoff.md` for `plan-change`. Inspect without editing the target
repository. Never implement, patch, prescribe file-level changes, write a test
blueprint, or route directly to `implement-plan`.

Keep drafts and measurements outside the installed skill, target repository,
and final output directory. Ecosystem documentation may validate a locally
selected mechanism; it never selects the mechanism.

## Start

Resolve `skill-root` to this directory and pass absolute draft and output paths:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --input draft=/absolute/draft.md --input output_dir=/absolute/output \
  --input scope=targeted --format json run
```

Run the returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`.

## Workflow

Follow [Optimization Contract](references/optimization-contract.md). Measure or
bound the baseline, reconcile the requested workflow, compare independent
candidates, and select one winner or a terminal state. Use
[Optimization Techniques](references/optimization-techniques.md) only for the
selected evidence branch.

Set exactly one handoff state: `plan-ready`, `needs-evidence`, or `no-change`.
A sweep accounts for every subsystem/pass pair and preserves resumable
deferments. Paths and symbols are evidence anchors, never an edit list.

## Completion and recovery

Complete only when the sealer returns exactly
`/absolute/output/optimization-handoff.md`, its typed receipt verifies, and no
other primary artifact exists. Pass only `plan-ready` output to `plan-change`.
`plan-change` v7 binds `RQ` anchors to the selected plan-ready `H-n` /
candidate material (not rejected candidates).

If evidence or candidate selection changes, regenerate the draft and repeat the
affected gates. A blocked measurement remains `needs-evidence`; never convert
uncertainty into a speculative plan or patch.
