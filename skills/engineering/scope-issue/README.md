# Scope Issue

`scope-issue` is the GitHub issue entry point to the proof-carrying planning
pipeline. It inventories and fetches issues from GitHub.com with `gh`, treats
all issue-authored text as untrusted claims, and grounds one selected issue
against a local checkout. GitHub Enterprise and non-`gh` providers are outside
this skill's supported scope.

## Shared Runtime

`scope-issue` and [`plan-change`](../plan-change/) carry byte-identical copies
of `scripts/plan_runtime.py`. Every runtime change must update both copies,
both skill versions, and both changelogs in the same change. CI compares the
runtime files byte-for-byte.

The runtime provides AST-grounded structured-fact verification for Python,
JavaScript and TypeScript, Kotlin, Go, Java, Rust, and Ruby. Recognized
tree-sitter languages fail with `fact.parser_dependency` when their pinned
grammar cannot be loaded. Other file types retain SHA-256 grounding without
invented AST verification.

## Handoff Contract

The handoff to `plan-change` consists of the validated issue artifact and the
absolute checkout path. Pass the artifact to `prepare_plan.py --request-file`
and re-ground its claims against that checkout.

The result is a finalized plan-contract v5 plan. Its evidence records bind both
the cited excerpt and complete file with SHA-256. A plan routed from
`scope-issue` also carries:

- `source-issue-plan-sha256`
- `source-base-commit`
- `source-issue-updated-at`

Those markers bind the senior plan to the validated issue artifact, checkout
commit, and issue revision used to produce it.

See the canonical [design-to-plan pipeline](../design-codebase/README.md) for
the alternative design handoff into `plan-change`.
