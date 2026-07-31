---
name: optimize-codebase
description: Run a multi-gate, evidence-backed optimization process for a named performance, build, CI, dependency, maintainability, or developer-experience workflow. Use targeted mode for a known pain and sweep mode only for explicit repository-wide discovery; implementation requires explicit authorization, with a strict Quick-Win fast path for already-authorized single-symbol changes.
version: 2.2.1
metadata:
  invocation: user-invoked
disable-model-invocation: true
user-invocable: true
---

# Optimize Codebase

## Purpose and authority

Select one evidence-backed leverage point for a named workflow. Local evidence
selects the mechanism; ecosystem documentation only validates that selection.
Treat implementation as unauthorized unless the user explicitly requested it.

Never write outside the selected candidate, retain a failed or inconclusive
patch, or weaken fast-path eligibility. Keep artifacts outside the installed
skill and use absolute paths.

## Start

Start with the trusted request and explicit path, scope, stage, report, and
authorization values:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --run-dir /absolute/run --input request_file=/absolute/request.md \
  --input path=full --input scope=targeted --input stage=plan \
  --input report=/absolute/run/report.md \
  --input implementation_authorized=no --format json doctor
```

Run each returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`. Apply deterministic classification unless hash-bound contrary
request or current-source evidence justifies the supported override.

## Next-step loop

Use `fast` only when every rule in [Fast Path](references/fast-path.md) is
already proved; otherwise use `full`. For full work, read [Glossary](references/glossary.md)
before [Optimization Protocol](references/optimization-protocol.md), then apply
the [Promotion Rubric](references/optimization-rubric.md).

Read [Documentation Research](references/docs-research-protocol.md),
[Ecosystem Leverage](references/ecosystem-leverage.md), or
[Optimization Patterns](references/optimization-patterns.md) only after a
baseline selects that branch. Use [Worked Examples](references/worked-examples.md)
only for artifact calibration. For a `plan-change` handoff, follow the exact
[Handoff Contract](references/handoff-contract.json).

Measure or bound the baseline, reconcile the request, compare independent
candidates, then plan or implement exactly one winner. A sweep must account for
every subsystem/pass pair and keep all deferments resumable.

## Completion and recovery

Complete only when the checker passes, every deferral and residual risk is
visible, and exactly one handoff state owns all required artifacts. An
implementation additionally needs attributable before/after evidence and a
recorded rollback state.

If scope, stage, or candidate selection changes, regenerate the scaffold and
repeat affected gates. Revert only the introduced patch when behavior regresses
or evidence is neutral, worse, or inconclusive.
