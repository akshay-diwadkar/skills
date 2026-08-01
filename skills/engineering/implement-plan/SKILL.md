---
name: implement-plan
description: Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report. Use when the user has an approved or written plan and asks to implement, apply, or build it. Vague plans are refused back to planning.
version: 2.0.0
metadata:
  implementation-contract: "3"
  invocation: user-invoked
  finalizer: "scripts/finalize_implementation.py"
  validation-required: "true"
disable-model-invocation: true
user-invocable: true
---

# Implement Plan

## Purpose and authority

Implement the exact approved plan as the smallest complete patch. The plan
limits behavior changes; repository evidence determines local form; the v3
implementation contract proves the result.

Accept only finalized plan-contract v6 plans.
Reject ambiguous, unfinalized, unsupported, receipt-mismatched, or materially
contradicted plans. Route semantic gaps to `plan-change`; never reinterpret
product intent during implementation. Preserve unrelated dirty work byte for
byte, never edit a dirty target without explicit authorization, and stop on a
concurrent target change.

## Start

Resolve `skill-root` to this directory. Use a new run directory outside both
the installed skill and target repository, and pass the exact finalized plan:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --run-dir /absolute/run --input plan_file=/absolute/final-plan.md \
  --format json doctor
```

Run each returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`.

## Next-step loop

1. Apply the intake, snapshots, dependency order, propagation, verification, and reconciliation rules in [Implementation Protocols](references/implementation-protocols.md).
2. Use [Bounded Delegation Protocol](references/delegation-protocol.md) for optional read-only review; the primary retains authority.
3. Treat [Implementation Contract](references/implementation-contract.json) as authoritative for fields, statuses, plan versions, and safety policy.
4. Apply [Code Quality Checklist](references/code-quality-checklist.md) to every touched file and final result.
5. Use [Implementation Hazards](references/implementation-hazards.md) at the matching stop condition; never restore a whole file, worktree, or branch automatically.
6. Use [Direct CLI Compatibility](references/cli-compatibility.md) only for supported lower-level entry points, including explicitly authorized dirty-target incorporation.

Implement every planned branch, error, side effect, blueprint, and test. Allow
unplanned edits only through the Mechanical Propagation Gate. Attribute a
failure as pre-existing only when the identical check failed in the recorded
baseline.

## Completion and recovery

Complete only when phase `complete` returns a validator-passing
`implementation.json` with status `complete` and a matching v3 SHA-256 receipt.
Report the plan version, changes, propagation, exact checks, residual risks,
and unresolved records.

On failure, preserve the bundle and agent-owned snapshots, follow the hazard's
recovery rule, and reverse only positively identified agent-owned hunks whose
context still matches. Never weaken plan or quality evidence to pass validation.
