# Changelog

## 5.0.0 - 2026-08-07

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
  placement, checkout freshness and dirtiness, non-empty status evidence,
  and explicit override/exclusion rules.
- Snapshot binding: the fetcher emits a sha256 digest of the snapshot into
  `metadata.source.snapshot_digest`, and checker and sealer reject any
  handoff whose digest does not match the snapshot on disk. Freshness is
  checker-derived: the handoff is stale when a snapshot issue `updated_at`
  postdates `fetched_at`.
- Membership is two-tier: `verified` snapshots declare the epic's children
  with a non-empty provenance mechanism and derived-at timestamp, bind the
  `CAND` set to children minus exclusions, and require any override to be a
  verified child; `unverified` snapshots declare an empty children map with
  null provenance, and candidates and the override only need to exist in the
  snapshot. Concrete children-of derivation mechanisms are deferred to
  scope-issue #209.
- Untrusted GitHub content must be quoted inside the machine-owned fence
  (`<!-- scope-issue: untrusted-begin/end -->`); the checker strips the
  fenced region before trusted parsing and rejects gap content between the
  heading and the begin marker.
- Alternatives use the `CAND-n why-not-now: <reason>` grammar, must name
  every other ready candidate, and are `none` only when the selected child is
  the sole ready candidate.
- Questions are typed `{question, reason}` with reason codes `selection-tie`
  and `clarification`; a `selection-tie` question requires at least two ready
  candidates.
- `blocked` is stage-aware: with a `SEL` record, at least one blocker must
  cite the selected child and an `F` record is required; without one,
  blockers must cite the epic or a declared candidate and no `SC`/`C`
  records may exist.
- `needs-decomposition` binds `decomposition_target` to the `CAND-n` record
  that needs decomposition.
- Single-issue mode (`metadata.mode: "single"`): exactly one snapshot issue,
  the epic is that issue, one `CAND` names it, and no override or exclusions
  are allowed.
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
