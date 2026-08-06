# Changelog

## 5.0.0 - 2026-08-06

- Redefine the contract as epic-aware (issue-plan contract v2): given one task
  and one epic, inventory candidates with verifiable `CAND` readiness and
  basis citations, select one ready child (`SEL`) or preserve an honest
  non-selection status: `needs-info`, `blocked`, `close-candidate`,
  `needs-decomposition`, `no-ready-issue`, `epic-complete`.
- Narrow only the selected child (`SC`, `F`, `D`, `C`); `E` records removed.
- Keep the `issue-handoff.md` receipt wire-compatible (kind `issue`, version
  1) for `plan-change` and `implement-plan`; the schema advances only in
  `metadata.contract_version: 2`.
- New `scope_inputs.json` input carries immutable anchors (task, epic,
  override, exclusions); the snapshot is sole source for candidate
  membership; the checker verifies sections in contract order, record
  placement, checkout freshness and dirtiness, tie-breaker obligations,
  non-empty status evidence, and explicit override/exclusion rules.
- Validate every rule from the JSON schema: record formats, numbering,
  section placement, status obligations, snapshot content-trust, and
  placeholder scanning now come from `issue-plan-contract.json`.

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
