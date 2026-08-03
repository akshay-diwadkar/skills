# Changelog

## 4.0.0 - 2026-08-03

- Stop at one read-only `issue-handoff.md` and remove execution and post-merge ownership.

## 2.3.0 - 2026-08-01

- Route new senior handoffs through stateless plan-contract v6 sealing.
- Accept finalized v5 handoffs through an isolated deprecated consumer for one
  release.

## 1.0.0 - 2026-07-29

- Establish skill versioning while retaining issue-plan contract v1 and the
  downstream plan-contract v5 handoff.
- Add Go, Java, Rust, and Ruby to the shared AST-grounded planning runtime.
- Document that shared-runtime and plan-contract changes must update both
  `scope-issue` and `plan-change` versions and changelogs together.
