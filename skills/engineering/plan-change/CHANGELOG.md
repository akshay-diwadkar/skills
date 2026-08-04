# Changelog

## 5.0.0 - 2026-08-04

- Introduce plan-contract v7 with required `Obligations` (`RQ`) records whose
  anchors verify against the exact request bytes and whose `covered_by` links
  must reference at least one success criterion and one change or verification
  record.
- Require the `CH` dependency graph: `depends_on`, locality, and reversibility
  are mandatory, with validation of dependency existence, self-reference,
  cycles, and one deterministic dependency-ordered execution sequence.
- Require propagation accounting for shared and non-tiny changes through owned
  `P` records or an evidence-backed `propagation: local|none` declaration, and
  protect irreversible changes with the high-risk tier and rollout section.
- Expand the intent set with `migration` and `operational` while keeping risk
  domains orthogonal, and extend task guidance with the matching branches.
- Add request-anchor obligation proofs to the sealed proof bundle and move the
  validation marker to version 7.
- Add an offline, provider-free plan-quality fixture suite with a deterministic
  scorer and a v7 sealing benchmark report.

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
