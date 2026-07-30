# Core handoff skills on the common CLI

This release makes `plan-change` and `implement-plan` self-contained common-CLI
skills with stable `doctor`, `start`, `next`, `validate`, and `finalize`
lifecycles. Skill-local adapters preserve argv-safe handoffs after standalone
installation and keep all run state outside tracked source.

The migration retains plan-contract v5 evidence, inventory, adversarial,
binding, and receipt checks, plus implementation-contract v3 dirty-worktree,
freshness, hash, quality-evidence, workspace-reconciliation, and receipt
checks. Existing direct scripts remain compatible lower-level entry points.
