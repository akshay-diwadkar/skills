---
name: implement-plan
description: Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report. Use when the user has an approved or written plan and asks to implement, apply, or build it. Vague plans are refused back to planning.
version: 3.3.0
metadata:
  invocation: user-invoked
  implementation-contract: "4"
  finalizer: "scripts/seal_implementation.py"
  validation-required: "true"
disable-model-invocation: true
user-invocable: true
---

# Implement Plan

## Purpose and authority

Implement the exact approved plan as the smallest complete patch. The plan
limits behavior changes; repository evidence determines local form; the v4
implementation contract proves the result.

Accept finalized plan-contract v6 or v7 plans with the typed request binding
(kind, version, and selected-item). Reject ambiguous, unfinalized, unsupported, receipt-mismatched, or materially contradicted plans. Route semantic gaps to
`plan-change`; never reinterpret product intent during implementation. Preserve unrelated dirty work byte for byte, never edit a dirty target without explicit
authorization, and stop on a concurrent target change.

## Start

Resolve `skill-root` to this directory and pass the exact sealed plan plus an
agent-owned implementation bundle:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --input plan_file=/absolute/final-plan.md \
  --input bundle=/absolute/implementation.json --format json doctor
```

Run each returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`.

## Next-step loop

1. Apply the intake, snapshots, dependency order, propagation, verification, and reconciliation rules in [Implementation Contract](references/implementation-contract.md).
2. Use [Bounded Delegation Protocol](references/delegation-protocol.md) for optional read-only review; the primary retains authority.
3. Treat [Implementation Contract](references/implementation-contract.json) as authoritative for fields, statuses, plan versions, and safety policy.
4. Apply the quality and compatibility checks in [Implementation Contract](references/implementation-contract.md).
5. Use [Safety and Recovery](references/safety-and-recovery.md) at the matching stop condition; never restore a whole file, worktree, or branch automatically.

Implement every planned branch, error, side effect, blueprint, and test. Allow
unplanned edits only through the Mechanical Propagation Gate. Attribute a
failure as pre-existing only when the identical check failed in the recorded
baseline. Apply `CH` records in the sealed `change_order`; never complete a
dependent change before its prerequisites.

## Completion and recovery

Complete only when sealing returns a validator-passing
`implementation.json` with status `complete` and a matching v4 SHA-256 receipt
that records the sealed plan-contract version. Report the plan version, change
order, changes, propagation, exact checks, residual risks, and unresolved
records.

On failure, preserve the bundle and agent-owned snapshots, follow the hazard's
recovery rule, and reverse only positively identified agent-owned hunks whose
context still matches. Never weaken plan or quality evidence to pass validation.
