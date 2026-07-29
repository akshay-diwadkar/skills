# Plan Change

`plan-change` produces a proof-carrying, repository-grounded implementation
plan without editing the target checkout. It accepts direct requests, design
handoffs, and validated artifacts from [`scope-issue`](../scope-issue/).

## Shared Runtime

`plan-change` and `scope-issue` carry byte-identical copies of
`scripts/plan_runtime.py`. Every runtime change must update both copies, both
skill versions, and both changelogs in the same change. CI compares the runtime
files byte-for-byte.

The runtime provides AST-grounded structured-fact verification for Python,
JavaScript and TypeScript, Kotlin, Go, Java, Rust, and Ruby. Recognized
tree-sitter languages fail with `fact.parser_dependency` when their pinned
grammar cannot be loaded. Other file types retain SHA-256 grounding without
invented AST verification.

## Scope-Issue Handoff

The issue handoff consists of a validated issue artifact and the absolute local
checkout path. Supply the artifact to `prepare_plan.py --request-file`; all
claims are re-grounded against the checkout.

The output is a finalized plan-contract v5 plan whose evidence records bind
the cited excerpt and complete file with SHA-256. For an issue-derived plan,
the final artifact also preserves:

- `source-issue-plan-sha256`
- `source-base-commit`
- `source-issue-updated-at`

Together these markers bind the final plan to the issue artifact, checkout
commit, and issue revision. `scope-issue` itself supports GitHub.com through
the `gh` CLI only.

See the canonical [design-to-plan pipeline](../design-codebase/README.md),
including the guarantees and limitations of `inventory.json`'s
`request_sha256`.
