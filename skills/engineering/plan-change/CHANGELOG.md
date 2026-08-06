# Changelog

## 5.0.0 - 2026-08-05

- Emit plan-contract v7 with required Obligations (`RQ`) records, explicit `CH`
  dependency/locality/reversibility fields, and expanded intents
  (`migration`, `operational`).
- Require propagation accounting for every `shared` change, force high-risk
  protections for irreversible changes, and keep sealing one-pass and
  agent-first without repository rediscovery.
- Add deterministic offline plan-quality fixtures separate from the sealing
  microbenchmark.

## 3.0.0 - 2026-08-01

- Replace the stateful v5 discovery workflow with agent-authored v6 drafts and
  one-pass targeted sealing.
- Remove inventory, exhaustive snapshots, classification, scaffolding,
  agent-supplied hashes, and legacy runtime commands.
- Add cached cited-file verification, generated proof hashes, targeted binding,
  stable repair diagnostics, and receipt verification.
- Reject malformed record-like lines and empty conditional sections, require
  actionable rollout content, and fail closed when an optional structured
  validator is unavailable.

## 1.0.0 - 2026-07-29

- Establish skill versioning while retaining plan-contract v5.
- Add Go, Java, Rust, and Ruby to the shared AST-grounded planning runtime.
- Document that shared-runtime and plan-contract changes must update both
  `scope-issue` and `plan-change` versions and changelogs together.
