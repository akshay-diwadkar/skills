# Changelog

## 3.0.0 - 2026-08-01

- Replace the stateful v5 discovery workflow with agent-authored v6 drafts and
  one-pass targeted sealing.
- Remove inventory, exhaustive snapshots, classification, scaffolding,
  agent-supplied hashes, and legacy runtime commands.
- Add cached cited-file verification, generated proof hashes, targeted binding,
  stable repair diagnostics, and receipt verification.

## 1.0.0 - 2026-07-29

- Establish skill versioning while retaining plan-contract v5.
- Add Go, Java, Rust, and Ruby to the shared AST-grounded planning runtime.
- Document that shared-runtime and plan-contract changes must update both
  `scope-issue` and `plan-change` versions and changelogs together.
