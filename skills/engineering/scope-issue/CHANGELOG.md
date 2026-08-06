# Changelog

## 5.0.0 - 2026-08-06

- Introduce the epic-aware issue-scope contract v2: one explicit user task and
  epic issue select and narrow one ready child, with honest `needs-decomposition`,
  `no-ready-issue`, `epic-complete`, and `selection-tie` terminal states.
- Separate the selection and narrowing stages with proportional evidence;
  scripts verify immutable anchors, override membership and readiness, derived
  ready frontiers, and status obligations.
- Enforce status exclusivity: at most one status evidence flag per handoff,
  questions only for `needs-info`, blockers only for `blocked`, no selection
  records in report states, `epic-complete` only when every candidate is
  completed or superseded, and `no-ready-issue` only when actionable work
  remains (including epics with no children).
- Allow an explicit child override to be honestly declined when its candidate
  is not ready; a declined override must never be selected.
- Reject dirty checkouts when sealing `plan-ready` or `close-candidate`
  evidence; `Issue-Level Decisions` is no longer a required plan-ready section.
- Keep contract v1 usable through the explicit compatibility mode when epic
  inputs are absent; v2 requires the task and epic anchors.
- Note: v2 `plan-ready` handoffs become consumable by `plan-change` once its
  intake accepts issue-handoff v2 receipts; v1 handoffs remain consumable today.

## 4.0.2 - 2026-08-05

- Clarify that `plan-change` v7 binds obligation anchors to outcome and protected-behavior regions.

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
