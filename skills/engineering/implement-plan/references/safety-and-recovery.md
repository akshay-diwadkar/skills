# Safety and Recovery

Preserve the smallest safe state at every stop. Keep snapshots and the bundle
outside the installed skill, and never broaden a plan because a check is noisy.

- Stop on a dirty-target conflict, concurrent change, missing dependency,
  changed behavior, missing anchor, or incompatible version; mark affected
  records unresolved and report the exact unblock condition.
- Reverse only positively identified agent-owned hunks whose context still
  matches. Preserve unrelated user work and all evidence needed to reproduce
  the stop.
- Never restore an entire file, worktree, index, commit, or branch automatically.
- If the plan, repository binding, or verification contract changes, return to
  `plan-change` and obtain a fresh sealed plan before continuing.
- Do not weaken evidence, omit a failed check, or claim completion to clear a
  blocked implementation.
